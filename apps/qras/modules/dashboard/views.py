from datetime import date, datetime
from datetime import timezone as dt_timezone
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from apps.qras.models.employee import (
    Employee,
    EmployeeSchedule
)
from apps.qras.models.attendance import (
    Attendance,
    LeaveRequest,
    OvertimeRequest,
    UndertimeRequest,
    HalfdayRequest,
    MissingLog
)
from apps.qras.models.management import (
    ShiftSchedule,
    ScheduleActivityLog
)
from apps.qras.modules.attendance.computation import compute_attendance_from_logs
from apps.qras.modules.auth.decorators import permission_required
from apps.qras.modules.auth.helpers import get_dept_queryset_filter


@method_decorator([permission_required('dashboard', 'read')], name='dispatch')
class DashboardView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request)
        if dept_filter is None:
            return render(request, 'pages/dashboard.django', {'dept_warning': True})

        # Build per-model dept filters since each has a different field path
        dept         = getattr(request.user, 'department', None)
        role         = getattr(request.user, 'role', None)
        is_dept_head = role and role.name == 'Department Head'

        ot_filter = {'attendance__employee__department': dept} if is_dept_head else {}
        ut_filter = {'attendance__employee__department': dept} if is_dept_head else {}
        hd_filter = {'employee__department': dept}             if is_dept_head else {}
        lv_filter = {'employee__department': dept}             if is_dept_head else {}
        ml_filter = {'employee__department': dept}             if is_dept_head else {}
        em_filter = {'department': dept}                       if is_dept_head else {}

        ot_pending = OvertimeRequest.objects.filter(status='PENDING', **ot_filter).count()
        ut_pending = UndertimeRequest.objects.filter(status='PENDING', **ut_filter).count()
        hd_pending = HalfdayRequest.objects.filter(status='PENDING', **hd_filter).count()
        lv_pending = LeaveRequest.objects.filter(status='PENDING', **lv_filter).count()
        ml_pending = MissingLog.objects.filter(status='PENDING', **ml_filter).count()
        ns_count   = Employee.objects.filter(
            is_active=True, is_resigned=False,
            attendance__isnull=False, **em_filter
        ).exclude(schedules__is_active=True).distinct().count()

        sal_filter = {'employee__department': dept} if is_dept_head else {}

        recent_activity = []

        for ml in MissingLog.objects.filter(**ml_filter).exclude(status='PENDING').select_related(
            'employee__position'
        ).order_by('-resolved_at')[:10]:
            time_val = ml.time_out if ml.log_type == 'time_out' else ml.time_in
            time_str = time_val.strftime('%I:%M %p').lstrip('0') if time_val else '—'
            verb     = 'Resolved' if ml.status == 'RESOLVED' else 'Dismissed'
            recent_activity.append({
                'type':     'ML',
                'employee': ml.employee,
                'activity': f"{verb} missing {ml.log_type.replace('_', ' ')} — {time_str}",
                'work_date': ml.date,
                'acted_at':  ml.resolved_at,
            })

        for sal in ScheduleActivityLog.objects.filter(**sal_filter).select_related(
            'employee__position', 'assigned_schedule', 'previous_schedule'
        ).order_by('-acted_at')[:10]:
            prev = sal.previous_schedule.name if sal.previous_schedule else 'none'
            recent_activity.append({
                'type':     'UN',
                'employee': sal.employee,
                'activity': f"Assigned to {sal.assigned_schedule.name} (prev: {prev})",
                'work_date': None,
                'acted_at':  sal.acted_at,
            })

        recent_activity.sort(
            key=lambda x: x['acted_at'] or datetime.min.replace(tzinfo=dt_timezone.utc),
            reverse=True
        )

        return render(request, 'pages/dashboard.django', {
            'ml_pending':      ml_pending,
            'recent_activity': recent_activity[:10],
            'ns_count':        ns_count,
        })

    def post(self, request):
        role = request.user.role
        if role.name != 'Admin' and not role.permissions.filter(module__code='dashboard', can_update=True).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized.'}, status=403)
        
        attendance_id        = request.POST.get("attendance_id")
        decision             = request.POST.get("decision")
        override_schedule_id = request.POST.get("override_schedule_id", "")

        if decision not in ("ASSIGNED",):
            return JsonResponse({"status": "invalid_decision"}, status=400)

        try:
            attendance = Attendance.objects.select_related(
                'employee', 'schedule'
            ).get(id=attendance_id)
        except Attendance.DoesNotExist:
            return JsonResponse({"status": "not_found"}, status=404)

        override_schedule = ShiftSchedule.objects.filter(id=override_schedule_id).first()
        if not override_schedule:
            return JsonResponse({"status": "no_schedule_selected"}, status=400)

        # Step 1: deactivate all existing schedules first
        EmployeeSchedule.objects.filter(
            employee=attendance.employee
        ).update(is_active=False)
        
        # Step 2: Create or update the new one
        EmployeeSchedule.objects.update_or_create(
            employee=attendance.employee,
            schedule=override_schedule,
            defaults={'is_active': True, 'effective_date': date.today()}
        )

        attendance = compute_attendance_from_logs(
            attendance.employee, attendance.date,
            schedule_override=override_schedule,
            skip_auto_approve=False
        )

        ot = OvertimeRequest.objects.filter(attendance=attendance, status='APPROVED').first()
        if ot:
            attendance.overtime_hours = ot.ot_hours
            attendance.save(update_fields=['overtime_hours'])

        return JsonResponse({
            "status":            "assigned",
            "new_schedule_name": override_schedule.name,
            "att_status":        attendance.att_status.status,
        })