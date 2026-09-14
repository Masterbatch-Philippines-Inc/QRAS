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
  Attendance,
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
 
 
class EmployeeCodeView(View):
    def get(self, request):
        return render(request, 'scanner/employee-code-input.html')

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
    template_name = 'scanner/qr.html'
 
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
    template_name = 'scanner/scan-captures.html'

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