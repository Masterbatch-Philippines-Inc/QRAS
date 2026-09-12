import re
import json as json_module
from datetime import datetime, time as dtime, timedelta, date as date_type, date as date_cls

import fitz  # PyMuPDF

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from app.employees.models import Employee
from app.attendance.helpers import record_attendance, check_duplicate_log, _flag_past_missing_logs
from app.authentication.decorators import role_required, permission_required
from django.utils.decorators import method_decorator


# # ─────────────────────────────────────────────────────────────────────────────
# #  LAZY EasyOCR — only loaded if text layer is absent (scanned/handwritten PDF)
# # ─────────────────────────────────────────────────────────────────────────────

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _reader


# # ─────────────────────────────────────────────────────────────────────────────
# #  DATE EXTRACTION
# # ─────────────────────────────────────────────────────────────────────────────

_DATE_PATTERNS = [
    r'[Dd]ate\s*[:\-]\s*([A-Za-z]+ \d{1,2},?\s*\d{4})',
    r'[Dd]ate\s*[:\-]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
    r'([A-Za-z]+ \d{1,2},?\s*\d{4})',               # bare fallback
]
_DATE_FORMATS = ['%B %d, %Y', '%B %d,%Y', '%m/%d/%Y', '%d/%m/%Y']


def _parse_date_from_text(text):
    for pat in _DATE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = re.sub(r',\s*', ', ', m.group(1).strip())
            for fmt in _DATE_FORMATS:
                try:
                    return datetime.strptime(raw, fmt).date()
                except ValueError:
                    continue
    return None


# # ─────────────────────────────────────────────────────────────────────────────
# #  TIME NORMALIZATION
# #  Handles 3-digit OCR misreads like "803" → "0803"
# # ─────────────────────────────────────────────────────────────────────────────

def _normalize_time(raw):
    raw = raw.strip()
    if len(raw) == 3:
        raw = '0' + raw
    return raw


# # ─────────────────────────────────────────────────────────────────────────────
# #  ROW PARSING
# #  Format: <row_num>  <Name, ...>  <t1> [t2] [t3] [t4]  [remarks]
# #  Times are 3–4 digit HHMM values.  Name ends just before first time.
# # ─────────────────────────────────────────────────────────────────────────────

_ROW_RE = re.compile(
    r'^(\d{1,3})\s+'           # row number (1–3 digits)
    r'(.+?)\s+'                # name — non-greedy, stops before first time
    r'(\d{3,4})'               # time 1
    r'(?:\s+(\d{3,4}))?'       # time 2
    r'(?:\s+(\d{3,4}))?'       # time 3
    r'(?:\s+(\d{3,4}))?'       # time 4
    r'\s*(.*)?$'               # optional remarks
)


def _parse_rows(text, base_date):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        m = _ROW_RE.match(line)
        if not m:
            continue

        row_num  = int(m.group(1))
        name_raw = m.group(2).strip().rstrip(',').strip()
        raw_times = [_normalize_time(m.group(i)) for i in range(3, 7) if m.group(i)]
        remarks  = (m.group(7) or '').strip()

        # Pair times: [t1, t2, t3, t4] → [(t1,t2), (t3,t4)]
        pairs = []
        i = 0

        while i < len(raw_times):
            t_in  = raw_times[i]
            t_out = raw_times[i + 1] if i + 1 < len(raw_times) else None
            if t_out is None and i == 0 and len(raw_times) == 1:
                pairs.append([None, t_in])  # single time = time-out only
            else:
                pairs.append([t_in, t_out])
            i += 2

        rows.append({
            'row_num':    row_num,
            'name_raw':   name_raw,
            'time_pairs': pairs,
            'remarks':    remarks,
            'date':       str(base_date),
        })

    return rows


# # ─────────────────────────────────────────────────────────────────────────────
# #  EMPLOYEE NAME MATCHING
# #  Input format: "Lastname, Firstname, MI"
# #  3-level fallback: exact → last+first-startswith → last-name-unique
# # ─────────────────────────────────────────────────────────────────────────────

def _match_employee(name_raw):
    parts = [p.strip() for p in name_raw.split(',')]
    last  = parts[0] if parts else ''
    first = parts[1] if len(parts) > 1 else ''
    first_word = first.split()[0] if first.split() else ''

    qs = Employee.objects.filter(is_active=True, is_resigned=False)

    # 1. Exact last + first
    hit = qs.filter(last_name__iexact=last, first_name__iexact=first).first()
    if hit:
        return hit

    # 2. Exact last + first starts-with
    if first_word:
        cands = qs.filter(last_name__iexact=last, first_name__istartswith=first_word)
        if cands.count() == 1:
            return cands.first()

    # 3. Exact last only — unique
    cands = qs.filter(last_name__iexact=last)
    if cands.count() == 1:
        return cands.first()

    return None


# # ─────────────────────────────────────────────────────────────────────────────
# #  TIME → TIMEZONE-AWARE DATETIME
# #  Night-shift detection: if out_hhmm < in_hhmm (as integers), add 1 day.
# # ─────────────────────────────────────────────────────────────────────────────

def _to_aware(hhmm, base_date, prev_hhmm=None):
    h, mi = int(hhmm[:2]), int(hhmm[2:])
    naive = datetime.combine(base_date, dtime(h, mi))
    if prev_hhmm:
        ph, pm = int(prev_hhmm[:2]), int(prev_hhmm[2:])
        if (h * 60 + mi) < (ph * 60 + pm):
            naive += timedelta(days=1)
    tz = timezone.get_current_timezone()
    return timezone.make_aware(naive, tz)


# # ─────────────────────────────────────────────────────────────────────────────
# #  OCR: reconstruct line-by-line text from EasyOCR bounding boxes
# #  Groups detected text by Y position (row ± 15px tolerance) then sorts by X.
# # ─────────────────────────────────────────────────────────────────────────────

def _extract_text_by_position(page):
    """
    Reconstruct reading-order lines from word bounding boxes.
    Handles PDFs where get_text() returns columns instead of rows.
    Groups words whose Y midpoint is within 8px of each other, then sorts by X.
    """
    words = page.get_text("words")
    if not words:
        return '', []

    lines = []
    for (x0, y0, x1, y1, word, *_) in words:
        mid_y = (y0 + y1) / 2
        placed = False
        for line in lines:
            if abs(line['y'] - mid_y) <= 8:
                line['tokens'].append((x0, word))
                placed = True
                break
        if not placed:
            lines.append({'y': mid_y, 'tokens': [(x0, word)]})

    lines.sort(key=lambda l: l['y'])
    flat_text = '\n'.join(
        ' '.join(w for _, w in sorted(line['tokens']))
        for line in lines
    )
    return flat_text, lines

_INOUT_RE = re.compile(r'^(in|out)$', re.IGNORECASE)

def _detect_column_slots(lines):
    """
    Find the header row and return the X-center of each In/Out column.
    Returns list of ('in'|'out', x_center) in left-to-right order.
    Expected result: [('in', x), ('out', x), ('in', x), ('out', x)]
    """
    for line in lines:
        col_headers = [(x, w) for x, w in line['tokens'] if _INOUT_RE.match(w)]
        if len(col_headers) >= 2:
            col_headers.sort(key=lambda t: t[0])
            return [(w.lower(), x) for x, w in col_headers]
    return None

_TIME_TOKEN_RE = re.compile(r'^\d{3,4}$')
_ROW_NUM_TOKEN_RE = re.compile(r'^\d{1,3}$')

def _parse_rows_positional(lines, slot_xs, base_date):
    """
    Parse employee rows using X position to assign times to the correct column.
    slot_xs: [('in', x), ('out', x), ('in', x), ('out', x)]
    """
    rows = []

    for line in lines:
        tokens_sorted = sorted(line['tokens'], key=lambda t: t[0])
        word_list = [w for _, w in tokens_sorted]
        
        row_num_x, row_num_token = next(
            ((x, w) for x, w in tokens_sorted if _ROW_NUM_TOKEN_RE.match(w)),
            (None, None)
        )
        if not row_num_token:
            continue

        time_tokens = [(x, _normalize_time(w)) for x, w in line['tokens']
                       if _TIME_TOKEN_RE.match(w)]
        if not time_tokens:
            continue

        # Assign each time value to the nearest column slot by X distance
        slot_values = [None] * len(slot_xs)
        for tx, tval in time_tokens:
            nearest = min(range(len(slot_xs)), key=lambda i: abs(slot_xs[i][1] - tx))
            slot_values[nearest] = tval

        # Build pairs: slot 0+1 = first pair, slot 2+3 = second pair
        pairs = []
        for i in range(0, len(slot_xs), 2):
            t_in  = slot_values[i]
            t_out = slot_values[i + 1] if i + 1 < len(slot_xs) else None
            if t_in or t_out:
                pairs.append([t_in, t_out])

        # Name = all tokens to the left of the first time token
        min_time_x  = min(tx for tx, _ in time_tokens)
        name_tokens = [w for x, w in tokens_sorted
                       if row_num_x < x < min_time_x and not _ROW_NUM_TOKEN_RE.match(w)]
        name_raw    = ' '.join(name_tokens).strip().rstrip(',').strip()

        # Remarks = tokens to the right of the last time token
        max_time_x     = max(tx for tx, _ in time_tokens)
        remark_tokens  = [w for x, w in tokens_sorted if x > max_time_x + 20]
        remarks        = ' '.join(remark_tokens).strip()

        rows.append({
            'row_num':    int(row_num_token),
            'name_raw':   name_raw,
            'time_pairs': pairs,
            'remarks':    remarks,
            'date':       str(base_date),
        })

    return rows

def _ocr_to_text(img_bytes):
    reader  = _get_reader()
    results = reader.readtext(img_bytes)          # [(bbox, text, conf), ...]

    if not results:
        return ''

    # Group into lines by top-y proximity
    lines = []
    for (bbox, text, _conf) in results:
        top_y = bbox[0][1]
        left_x = bbox[0][0]
        placed = False
        for line in lines:
            if abs(line['y'] - top_y) <= 15:
                line['tokens'].append((left_x, text))
                placed = True
                break
        if not placed:
            lines.append({'y': top_y, 'tokens': [(left_x, text)]})

    lines.sort(key=lambda l: l['y'])
    return '\n'.join(
        ' '.join(t for _, t in sorted(line['tokens']))
        for line in lines
    )


# # ─────────────────────────────────────────────────────────────────────────────
# #  VIEWS
# # ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('settings_smart_manual_attendance', 'read')], name='dispatch')
class ScanUploadView(LoginRequiredMixin, View):
    """Renders the upload/preview page."""

    def get(self, request):
        employees = list(
            Employee.objects.filter(is_active=True, is_resigned=False)
            .order_by('last_name', 'first_name')
            .values('id', 'last_name', 'first_name', 'middle_name')
        )
        return render(request, 'attendance/smart-manual-attendance.html', {
            'employees_json': json_module.dumps(employees),
        })


@method_decorator([permission_required('settings_smart_manual_attendance', 'read')], name='dispatch')
class ScanUploadParseView(LoginRequiredMixin, View):
    """
    POST: receives uploaded PDF, extracts text per page (falls back to EasyOCR
    for scanned pages), parses rows, matches employees, returns JSON preview.
    """

    def post(self, request):
        pdf_file = request.FILES.get('pdf')
        if not pdf_file:
            return JsonResponse({'error': 'No file uploaded.'}, status=400)

        pdf_bytes = pdf_file.read()
        try:
            doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        except Exception as e:
            return JsonResponse({'error': f'Cannot open PDF: {e}'}, status=400)

        pages_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # ── Try text layer first ──────────────────────────────────────
            text, lines = _extract_text_by_position(page)

            if len(text) < 80:
                try:
                    pix       = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img_bytes = pix.tobytes('png')
                    text      = _ocr_to_text(img_bytes)
                    lines     = []   # OCR path has no position data; fall back to text parser
                except Exception as e:
                    ...
                    continue

            page_date = _parse_date_from_text(text)

            if page_date and lines:
                slot_xs  = _detect_column_slots(lines)
                raw_rows = _parse_rows_positional(lines, slot_xs, page_date) if slot_xs else _parse_rows(text, page_date)
            elif page_date:
                raw_rows = _parse_rows(text, page_date)
            else:
                raw_rows = []

            parsed_rows = []
            for row in raw_rows:
                emp = _match_employee(row['name_raw'])
                parsed_rows.append({
                    'row_num':          row['row_num'],
                    'name_raw':         row['name_raw'],
                    'employee_id':      emp.id if emp else None,
                    'employee_display': f"{emp.last_name}, {emp.first_name}" if emp else None,
                    'match_status':     'matched' if emp else 'unmatched',
                    'time_pairs':       row['time_pairs'],
                    'remarks':          row['remarks'],
                    'date':             row['date'],
                    'skip':             False,
                })

            pages_data.append({
                'page':  page_num + 1,
                'date':  str(page_date) if page_date else None,
                'rows':  parsed_rows,
                'error': None,
            })

        doc.close()
        return JsonResponse({'pages': pages_data})


@method_decorator([permission_required('settings_smart_manual_attendance', 'create')], name='dispatch')
class ScanUploadSaveView(LoginRequiredMixin, View):
    """
    POST: receives confirmed records (JSON), saves each time entry via
    record_attendance (same as manual attendance).
    """

    def post(self, request):
        try:
            payload = json_module.loads(request.body)
        except json_module.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)

        records = payload.get('records', [])
        saved, errors = 0, []
        affected_dates = set()

        for rec in records:
            emp_id     = rec.get('employee_id')
            date_str   = rec.get('date')
            time_pairs = rec.get('time_pairs', [])

            if not emp_id or not date_str:
                errors.append({
                    'row':  rec.get('row_num'),
                    'name': rec.get('name_raw'),
                    'error': 'Missing employee or date.',
                })
                continue

            try:
                emp       = Employee.objects.get(id=emp_id)
                base_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except Exception as e:
                errors.append({'row': rec.get('row_num'), 'name': rec.get('name_raw'), 'error': str(e)})
                continue

            for pair in time_pairs:
                t_in  = pair[0] if pair else None
                t_out = pair[1] if len(pair) > 1 else None

                if not t_in and not t_out:
                    continue

                try:
                    if t_in:
                        dup_in = check_duplicate_log(emp, base_date, 'time_in')
                        if dup_in:
                            errors.append({
                                'row':  rec.get('row_num'),
                                'name': rec.get('name_raw'),
                                'error': f"Duplicate time-in for {emp.employee_id} on {base_date}.",
                            })
                        else:
                            ts_in = _to_aware(t_in, base_date)
                            record_attendance(
                                employee=emp,
                                date=base_date,
                                timestamp=ts_in,
                                is_time_in=True,
                                is_time_out=False,
                                att_source='manual',
                            )
                            affected_dates.add(base_date)

                    if t_out:
                        ts_out   = _to_aware(t_out, base_date, prev_hhmm=t_in)
                        out_date = ts_out.astimezone(timezone.get_current_timezone()).date()

                        dup_out = check_duplicate_log(emp, out_date, 'time_out')
                        if not dup_out or (isinstance(dup_out, dict) and dup_out.get('status') == 'no_time_in'):
                            record_attendance(
                                employee=emp,
                                date=out_date,
                                timestamp=ts_out,
                                is_time_in=False,
                                is_time_out=True,
                                att_source='manual',
                            )
                            affected_dates.add(out_date)

                    saved += 1

                except Exception as e:
                    errors.append({
                        'row':  rec.get('row_num'),
                        'name': rec.get('name_raw'),
                        'error': str(e),
                    })

        # today = date_type.today()
        # for d in affected_dates:
        #     if d < today:
        #         detect_and_sync_missing_logs(d)

        # Final pass — rescan all affected employees now that all logs are
        # in the database. This catches dates whose later-log proof only
        # appeared partway through the save loop.
        affected_employees = {
            Employee.objects.filter(id=rec.get('employee_id')).first()
            for rec in records if rec.get('employee_id')
        }
        earliest_date = min(affected_dates) if affected_dates else None
        for emp in affected_employees:
            if emp:
                _flag_past_missing_logs(
                    emp,
                    date_cls.today(),
                    lookback_start=earliest_date,
                )

        return JsonResponse({'saved': saved, 'errors': errors})

