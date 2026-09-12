import json
from datetime import datetime, timezone as dt_timezone


def build_attendance_payload(since, dept=None, user=None):
    from django.utils import timezone
    from django.db.models import Max, Count, Q
    from app.attendance.models import Attendance, AttendanceStatus, AttendanceLog
    from app.authentication.helpers import get_self_exclude

    try:
        # Resolve self_exclude from user directly (not request)
        self_exclude = None
        if user:
            linked_emp = getattr(user, 'employee', None)
            if linked_emp:
                self_exclude = linked_emp.pk

        dept_filter = {'employee__department': dept} if dept else {}

        changed_logs = AttendanceLog.objects.filter(
            created_at__gt=since,
            **dept_filter
        )
        if self_exclude:
            changed_logs = changed_logs.exclude(employee__pk=self_exclude)

        employee_pks = list(changed_logs.values_list('employee', flat=True).distinct())

        if not employee_pks:
            return json.dumps({'since': timezone.now().isoformat(), 'rows': []}), timezone.now()

        latest_dates = list(
            Attendance.objects
            .filter(employee__pk__in=employee_pks)
            .values('employee')
            .annotate(latest_date=Max('date'))
        )
        latest_date_map = {item['employee']: item['latest_date'] for item in latest_dates}

        flag_rows = (
            AttendanceStatus.objects
            .filter(attendance__employee__pk__in=employee_pks)
            .values('attendance__employee')
            .annotate(
                missing_log_count=Count('pk', filter=Q(has_missing_log=True)),
                undertime_count=Count('pk',   filter=Q(is_undertime=True)),
                halfday_count=Count('pk',     filter=Q(is_halfday=True)),
                overtime_count=Count('pk',    filter=Q(is_overtime=True)),
            )
        )
        flag_map = {row['attendance__employee']: row for row in flag_rows}

        unscheduled_rows = (
            Attendance.objects
            .filter(employee__pk__in=employee_pks, schedule__isnull=True)
            .values('employee')
            .annotate(unscheduled_count=Count('pk'))
        )
        unscheduled_map = {row['employee']: row['unscheduled_count'] for row in unscheduled_rows}

        latest_atts = (
            Attendance.objects
            .filter(employee__pk__in=employee_pks)
            .select_related('employee', 'employee__position', 'schedule', 'att_status')
        )
        att_map = {}
        for att in latest_atts:
            emp_pk = att.employee.pk
            if att.date == latest_date_map.get(emp_pk):
                att_map[emp_pk] = att

        rows = []
        for emp_pk in employee_pks:
            att = att_map.get(emp_pk)
            if not att:
                continue
            try:
                s = att.att_status
            except AttendanceStatus.DoesNotExist:
                continue

            flags = flag_map.get(emp_pk, {})
            emp = att.employee
            middle = f' {emp.middle_name}' if emp.middle_name else ''

            rows.append({
                'employee_id':        emp.employee_id,
                'full_name':          f'{emp.last_name}, {emp.first_name}{middle}',
                'position':           emp.position.title if emp.position else '—',
                'department':         str(emp.department) if emp.department else '—',
                'has_schedule':       att.schedule is not None,
                'last_date':          att.date.strftime('%b %d, %Y'),
                'is_regular_holiday': s.is_regular_holiday,
                'is_special_holiday': s.is_special_holiday,
                'unscheduled_count':  unscheduled_map.get(emp_pk, 0),
                'missing_log_count':  flags.get('missing_log_count', 0),
                'undertime_count':    flags.get('undertime_count', 0),
                'halfday_count':      flags.get('halfday_count', 0),
                'overtime_count':     flags.get('overtime_count', 0),
            })

        now = timezone.now()
        return json.dumps({'since': now.isoformat(), 'rows': rows}), now

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'[ATT SSE] Exception: {e}')
        now = timezone.now()
        return json.dumps({'since': now.isoformat(), 'rows': []}), now

