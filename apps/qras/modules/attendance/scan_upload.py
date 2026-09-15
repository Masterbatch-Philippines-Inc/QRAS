import re
from datetime import datetime, time as dtime, timedelta, date as date_type, date as date_cls
from django.utils import timezone
from apps.qras.models.employee import Employee


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