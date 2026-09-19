from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count

from apps.qras.models.employee import (
  Employee
)
from apps.qras.models.attendance import (
  AttendanceLog,
  AttendanceLogAudit
)
from apps.qras.models.scanner import (
  ScanCapture
)
from apps.qras.modules.scanner.utils import decode_base64_image
from apps.qras.modules.attendance.helpers import record_attendance
from datetime import timedelta, date
from apps.qras.modules.auth.decorators import permission_required
from apps.qras.modules.auth.helpers import get_dept_queryset_filter
from collections import defaultdict
from apps.qras.modules.features.clock_offset.utils import get_clock_offset


from apps.qras.modules.attendance.helpers import record_attendance, check_duplicate_log, _flag_past_missing_logs
from apps.qras.modules.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
import pymupdf
import json as json_module
from datetime import datetime, timedelta, date, date as date_cls
 
 
class EmployeeCodeView(View):
    def get(self, request):
        return render(request, 'pages/scanner/codes.django')

class EmployeeLookupView(View):
    def get(self, request, employee_id):
        try:
            emp = Employee.objects.select_related(
                'department', 'position'
            ).get(employee_id=employee_id, is_active=True)
        except Employee.DoesNotExist:
            return JsonResponse({'found': False, 'message': 'Employee not found.'}, status=404)

        return JsonResponse({
            'found':       True,
            'id':          emp.id,
            'employee_id': emp.employee_id,
            'name':        f'{emp.last_name}, {emp.first_name}',
            'first_name':  emp.first_name,
            'last_name':   emp.last_name,
            'department':  emp.department.name if emp.department else '—',
            'position':    emp.position.title  if emp.position  else '—',
        })

class ScanAttendanceView(View):
    template_name = 'pages/scanner/qrs.django'
 
    def post(self, request):
        emp_id = request.POST.get("employee_id")
        action = request.POST.get("log_action")  # time_in / time_out
 
        if not emp_id or not action:
            return JsonResponse({"status": "failed"})
 
        # 1. Check employee
        try:
            emp = Employee.objects.get(employee_id=emp_id, is_active=True)
        except Employee.DoesNotExist:
            return JsonResponse({"status": "emp_not_found"})
        now = timezone.localtime() - timedelta(minutes=get_clock_offset())
        today = now.date()
 
        # 2. Get latest log today
        last_log = AttendanceLog.objects.filter(
            employee=emp,
            date=today,
            is_replaced=False
        ).order_by('-timestamp').first()
 
        # 3. DUPLICATE CHECK
        if last_log:
            if action == "time_in" and last_log.is_time_in:
                return JsonResponse({
                    "status": "duplicate",
                    "last_record": {
                        "lr_empFN": emp.first_name,
                        "time": timezone.localtime(last_log.timestamp).strftime("%I:%M:%S %p"),
                        "log_type": "TIME IN",
                        "date": timezone.localtime(last_log.timestamp).strftime("%b %d, %Y")
                    }
                })
            if action == "time_out" and last_log.is_time_out:
                return JsonResponse({
                    "status": "duplicate",
                    "last_record": {
                        "lr_empFN": emp.first_name,
                        "time": timezone.localtime(last_log.timestamp).strftime("%I:%M:%S %p"),
                        "log_type": "TIME OUT",
                        "date": timezone.localtime(last_log.timestamp).strftime("%b %d, %Y")
                    }
                })
 
        # 4. FLAG TIME OUT without prior TIME IN
        no_prior_time_in = False
        if action == "time_out":
            has_time_in = AttendanceLog.objects.filter(
                employee=emp,
                date=today,
                is_time_in=True,
                is_replaced=False
            ).exists()
            if not has_time_in:
                no_prior_time_in = True
 
        # 5. SAVE LOG
        record_attendance(
            employee=emp,
            date=today,
            timestamp=now,
            is_time_in=(action == "time_in"),
            is_time_out=(action == "time_out"),
            att_source='qr'
        )
        
        # 6. Capture Scan
        log = AttendanceLog.objects.filter(
            employee=emp,
            date=today,
            is_time_in=(action == "time_in"),
            is_time_out=(action == "time_out"),
            is_replaced=False
        ).order_by('-timestamp').first()

        image_data = request.POST.get('captured_image')
        if image_data and log:
            image_file = decode_base64_image(image_data, emp.employee_id, action)
            if image_file:
                ScanCapture.objects.create(
                    employee=emp,
                    attendance=log,
                    image=image_file,
                    action=action,
                )
 
        if no_prior_time_in:
            return JsonResponse({"status": "time_recorded_no_time_in"})

        return JsonResponse({
            "status": "time_recorded",
            "log_type": "IN" if action == "time_in" else "OUT"
        })
 
    def get(self, request):
        return render(request, self.template_name)

class UpdateAttendanceView(View):

    def post(self, request):
        emp_id   = request.POST.get('employee_id')
        action   = request.POST.get('log_action')
        employee = Employee.objects.filter(employee_id=emp_id).first()
        if not employee:
            return JsonResponse({"status": "emp_not_found"})
        now = timezone.localtime(timezone.now()) - timedelta(minutes=get_clock_offset())
        today = now.date()

        # Find the duplicate log and flag it instead of deleting
        old_log = AttendanceLog.objects.filter(
            employee=employee,
            date=today,
            is_time_in=(action == "time_in"),
            is_time_out=(action == "time_out"),
            is_replaced=False
        ).order_by('timestamp').first()
        if old_log:
            old_log.is_replaced = True
            old_log.save(update_fields=['is_replaced'])
            AttendanceLogAudit.objects.create(
                original_log=old_log,
                employee=employee,
                original_time=old_log.timestamp,
                replaced_by=request.user if request.user.is_authenticated else None,
                log_type=action,
            )
        record_attendance(
            employee=employee,
            date=today,
            timestamp=now,
            is_time_in=(action == "time_in"),
            is_time_out=(action == "time_out"),
            att_source='qr'
        )
        return JsonResponse({"status": "overwritten"})

    def get(self, request):
        return redirect('scanner')


@method_decorator(permission_required('attendance', 'read'), name='dispatch')
class ScanCaptureListView(View):
    template_name = 'pages/schedule/captures.django'

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='department')
        if dept_filter is None:
            return render(request, self.template_name, {'dept_warning': True, 'employees': []})

        employees = Employee.objects.filter(
            is_active=True, **dept_filter
        ).select_related('position', 'department').order_by('last_name', 'first_name')

        return render(request, self.template_name, {'employees': employees})


@method_decorator(permission_required('attendance', 'read'), name='dispatch')
class ScanCaptureDataView(View):

    def get(self, request, employee_id):
        try:
            emp = Employee.objects.select_related('position').get(
                employee_id=employee_id, is_active=True
            )
        except Employee.DoesNotExist:
            return JsonResponse({'error': 'Employee not found.'}, status=404)


        date_from_str = request.GET.get('date_from')
        date_to_str   = request.GET.get('date_to')

        try:
            date_from = date.fromisoformat(date_from_str) if date_from_str else date.today().replace(day=1)
            date_to   = date.fromisoformat(date_to_str)   if date_to_str   else date.today()
        except ValueError:
            date_from = date.today().replace(day=1)
            date_to   = date.today()

        captures = ScanCapture.objects.filter(
            employee=emp,
            captured_at__date__gte=date_from,
            captured_at__date__lte=date_to,
        ).order_by('-captured_at').only('captured_at', 'action', 'image')

        employee_name = f'{emp.last_name}, {emp.first_name}'

        grouped = defaultdict(list)
        for cap in captures:
            local_dt = timezone.localtime(cap.captured_at)
            grouped[local_dt.strftime('%Y-%m-%d')].append({
                'time':      local_dt.strftime('%I:%M:%S %p'),
                'action':    'Time In' if cap.action == 'time_in' else 'Time Out',
                'image_url': cap.image.url,
            })

        data = [
            {'date': day, 'captures': entries}
            for day, entries in sorted(grouped.items(), reverse=True)
        ]

        return JsonResponse({
            'employee_name': employee_name,
            'date_from':     date_from.isoformat(),
            'date_to':       date_to.isoformat(),
            'days':          data,
        })


@method_decorator(permission_required('attendance', 'read'), name='dispatch')
class ScanCaptureSummaryView(View):

    def get(self, request):
        date_from_str = request.GET.get('date_from')
        date_to_str   = request.GET.get('date_to')

        try:
            date_from = date.fromisoformat(date_from_str) if date_from_str else date.today().replace(day=1)
            date_to   = date.fromisoformat(date_to_str)   if date_to_str   else date.today()
        except ValueError:
            date_from = date.today().replace(day=1)
            date_to   = date.today()

        counts = (
            ScanCapture.objects
            .filter(captured_at__date__gte=date_from, captured_at__date__lte=date_to)
            .values('employee__employee_id')
            .annotate(total=Count('id'))
        )

        return JsonResponse({
            'counts': {row['employee__employee_id']: row['total'] for row in counts}
        })

class CheckTimeInStatusView(View):
    def get(self, request):
        emp_id = request.GET.get('employee_id')
        if not emp_id:
            return JsonResponse({'status': 'failed'})

        try:
            emp = Employee.objects.get(employee_id=emp_id, is_active=True)
        except Employee.DoesNotExist:
            return JsonResponse({'status': 'emp_not_found'})

        now = timezone.localtime() - timedelta(minutes=get_clock_offset())
        today = now.date()

        has_time_in = AttendanceLog.objects.filter(
            employee=emp, date=today, is_time_in=True, is_replaced=False
        ).exists()

        return JsonResponse({'status': 'ok', 'has_time_in': has_time_in})




@method_decorator([permission_required('settings_smart_manual_attendance', 'read')], name='dispatch')
class ScanUploadView(LoginRequiredMixin, View):
    """Renders the upload/preview page."""

    def get(self, request):
        employees = list(
            Employee.objects.filter(is_active=True, is_resigned=False)
            .order_by('last_name', 'first_name')
            .values('id', 'last_name', 'first_name', 'middle_name')
        )
        return render(request, 'pages/attendance/smart_manual_entry.django', {
            'employees_json': json_module.dumps(employees),
        })


@method_decorator([permission_required('settings_smart_manual_attendance', 'read')], name='dispatch')
class ScanUploadParseView(LoginRequiredMixin, View):
    """
    POST: receives uploaded PDF, extracts text per page (falls back to EasyOCR
    for scanned pages), parses rows, matches employees, returns JSON preview.
    """

    def post(self, request):
        
        from apps.qras.modules.attendance.scan_upload import (
            _extract_text_by_position,
            _ocr_to_text,
            _parse_date_from_text,
            _detect_column_slots,
            _parse_rows_positional,
            _parse_rows,
            _match_employee
        )
        
        pdf_file = request.FILES.get('pdf')
        if not pdf_file:
            return JsonResponse({'error': 'No file uploaded.'}, status=400)

        pdf_bytes = pdf_file.read()
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype='pdf')
        except Exception as e:
            return JsonResponse({'error': f'Cannot open PDF: {e}'}, status=400)

        pages_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # ── Try text layer first ──────────────────────────────────────
            text, lines = _extract_text_by_position(page)

            if len(text) < 80:
                try:
                    pix       = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
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

        from apps.qras.modules.attendance.scan_upload import _to_aware
        
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

