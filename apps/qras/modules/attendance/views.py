import json
from datetime import datetime, timedelta
from datetime import date as date_type
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render
from django.db.models import Max, Count, Q

from apps.qras.models.employee import (
    Employee, 
    EmployeeRestDay
)
from apps.qras.models.attendance import (
    Attendance,
    AttendanceStatus,
    AttendanceLog,
    AttendanceLogAudit,
    MissingLog
)
from apps.qras.modules.attendance.helpers import (
    format_hours_to_text, 
    resolve_display_status,
    check_duplicate_log, 
    record_attendance, 
)
from apps.qras.modules.auth.decorators import (
    role_required,
    permission_required
)
from apps.qras.modules.auth.helpers import (
    get_dept_queryset_filter,
    get_self_exclude
)


@method_decorator([permission_required('attendance', 'read')], name='dispatch')
class AttendanceRecordView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='employee__department')
        if dept_filter is None:
            return render(request, 'attendance/attendance-records.html', {'dept_warning': True})

        self_exclude = get_self_exclude(request)

        latest_dates = list(
            Attendance.objects
            .filter(**dept_filter)
            .values('employee')
            .annotate(latest_date=Max('date'))
        )
        if self_exclude:
            latest_dates = [i for i in latest_dates if i['employee'] != self_exclude]

        employee_pks    = [item['employee'] for item in latest_dates]
        latest_date_map = {item['employee']: item['latest_date'] for item in latest_dates}

        #── Bulk query 1: flag counts per employee across all their records ──────────
        flag_rows = (
            AttendanceStatus.objects
            .filter(attendance__employee__pk__in=employee_pks)
            .values('attendance__employee')
            .annotate(
                missing_log_count = Count('pk', filter=Q(has_missing_log=True)),
                undertime_count   = Count('pk', filter=Q(is_undertime=True)),
                halfday_count     = Count('pk', filter=Q(is_halfday=True)),
                overtime_count    = Count('pk', filter=Q(is_overtime=True)),
            )
        )
        flag_map = {row['attendance__employee']: row for row in flag_rows}

        #── Bulk query 2: unscheduled count per employee ──────────────────────────────
        unscheduled_rows = (
            Attendance.objects
            .filter(employee__pk__in=employee_pks, schedule__isnull=True)
            .values('employee')
            .annotate(unscheduled_count=Count('pk'))
        )
        unscheduled_map = {row['employee']: row['unscheduled_count'] for row in unscheduled_rows}

        #── Bulk query 3: latest attendance records (one per employee) ────────────────
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

        #── Build records using only dict lookups — zero extra queries ───────────────
        records = []
        for emp_pk in employee_pks:
            att = att_map.get(emp_pk)
            if not att:
                continue

            try:
                s = att.att_status
            except AttendanceStatus.DoesNotExist:
                continue

            flags         = flag_map.get(emp_pk, {})
            records.append({
                'employee':          att.employee,
                'last_date':         att.date,
                'schedule':          att.schedule,
                'total_hours':       format_hours_to_text(att.total_work_hours),
                'display_status':    resolve_display_status(s),
                'is_present':        s.is_present,
                'is_late':           s.is_late,
                'is_halfday':        s.is_halfday,
                'is_completed':      s.is_completed,
                'is_overtime':       s.is_overtime,
                'is_undertime':      s.is_undertime,
                'is_absent':         s.is_absent,
                'is_regular_holiday': s.is_regular_holiday,
                'is_special_holiday': s.is_special_holiday,
                'has_schedule':       att.schedule is not None,
                'missing_log_count':  flags.get('missing_log_count', 0),
                'undertime_count':    flags.get('undertime_count', 0),
                'halfday_count':      flags.get('halfday_count', 0),
                'overtime_count':     flags.get('overtime_count', 0),
                'unscheduled_count':  unscheduled_map.get(emp_pk, 0),
            })

        records.sort(key=lambda x: (
            x['employee'].last_name.lower(),
            x['employee'].first_name.lower()
        ))

        return render(request, 'attendance/attendance-records.html', {'records': records})


@method_decorator([permission_required('attendance', 'read')], name='dispatch')
class EmployeeAttendanceLogsView(View):

    def get(self, request):
        employee_id = request.GET.get('employee_id')

        logs = AttendanceLog.objects.filter(
            employee__employee_id=employee_id,
            is_replaced=False
        ).order_by('-date', 'timestamp')

        attendances = Attendance.objects.filter(
            employee__employee_id=employee_id
        ).select_related('schedule', 'att_status', 'ot_request')
        attendance_map = {att.date: att for att in attendances}

        grouped = {}
        for log in logs:
            d = log.date
            if d not in grouped:
                grouped[d] = {"time_in": None, "time_out": None}
            if log.is_time_in and not grouped[d]["time_in"]:
                grouped[d]["time_in"] = timezone.localtime(log.timestamp).strftime("%I:%M:%S %p")
            elif log.is_time_out:
                grouped[d]["time_out"] = timezone.localtime(log.timestamp).strftime("%I:%M:%S %p")

        data = []
        for d, val in grouped.items():
            att = attendance_map.get(d)

            try:
                s = att.att_status if att else None
            except AttendanceStatus.DoesNotExist:
                s = None

            att_status_val = s.status if s else 'PENDING'
            display_status = resolve_display_status(s) if s else 'PENDING'

            credited = s.credited_hours if s else None
            is_pending = att_status_val == 'PENDING'

            data.append({
                "date":             d.strftime("%Y-%m-%d"),
                "time_in":          val["time_in"],
                "time_out":         val["time_out"],
                "schedule":         att.schedule.name if att and att.schedule else None,
                "total_work_hours": format_hours_to_text(att.total_work_hours) if att else None,
                "credited_hours":   None  if is_pending else format_hours_to_text(credited),
                "overtime_hours":   format_hours_to_text(att.overtime_hours)   if att else None,
                "undertime_hours":  format_hours_to_text(att.undertime_hours)  if att else None,
                "late_hours":       format_hours_to_text(att.late_hours)       if att else None,
                "approval_status":  att_status_val,
                "display_status":   display_status,
                "is_completed":   False if is_pending else (s.is_completed    if s else False),
                "is_absent":      False if is_pending else (s.is_absent       if s else False),
                "is_late":        False if is_pending else (s.is_late         if s else False),
                "is_halfday":     False if is_pending else (s.is_halfday      if s else False),
                "is_overtime":    False if is_pending else (s.is_overtime     if s else False),
                "ot_approved":    att.ot_request.status == 'APPROVED' if att and hasattr(att, 'ot_request') and att.ot_request is not None else False,
                "is_ot_exempt":   att.employee.group_memberships.filter(group__ot_filing_exempted=True).exists() if att else False,
                "full_name":      f"{att.employee.last_name}, {att.employee.first_name}" if att else '',
                "is_undertime":   False if is_pending else (s.is_undertime    if s else False),
                "has_night_diff": False if is_pending else (s.has_night_diff  if s else False),
                "is_regular_holiday": False if is_pending else (s.is_regular_holiday if s else False),
                "is_special_holiday": False if is_pending else (s.is_special_holiday if s else False),
                "is_sunday":      False if is_pending else (s.is_sunday       if s else False),
                "has_missing_log":  s.has_missing_log if s else False,
            })

        return JsonResponse({"logs": data})


@method_decorator([permission_required('attendance', 'create')], name='dispatch')
class ManualAttendanceView(LoginRequiredMixin, View):

    def get(self, request):
        employees = Employee.objects.filter(
            is_active=True, is_resigned=False
        ).values('employee_id', 'first_name', 'last_name'
        ).order_by('last_name', 'first_name')
        return render(request, 'attendance/manual-attendance.html', {
            'employees': employees,
        })

    def post(self, request):
        try:
            data = json.loads(request.body)
            affected_dates = set()
            for entry in data:
                try:
                    employee    = Employee.objects.get(employee_id=entry.get('employee_id'))
                    parsed_date = datetime.strptime(entry.get('date'), '%Y-%m-%d').date()
                    action      = entry.get('status')

                    dup = check_duplicate_log(
                        employee, parsed_date,
                        'time_in' if action == 'in' else 'time_out'
                    )
                    if dup and dup.get('status') == 'duplicate':
                        old_log = AttendanceLog.objects.filter(
                            employee=employee,
                            date=parsed_date,
                            is_time_in=(action == 'in'),
                            is_time_out=(action == 'out'),
                            is_replaced=False
                        ).order_by('timestamp').first()
                        return JsonResponse({
                            "status": "duplicate",
                            "employee_id": employee.employee_id,
                            "employee_name": employee.first_name,
                            "log_action": action,
                            "date": parsed_date.strftime('%Y-%m-%d'),
                            "time": entry.get('time'),
                            "earlier_time": timezone.localtime(old_log.timestamp).strftime("%I:%M:%S %p") if old_log else None,
                            "earlier_date": parsed_date.strftime("%b %d, %Y"),
                            "log_type": "TIME IN" if action == 'in' else "TIME OUT",
                        }, status=200)

                    local_time = timezone.make_aware(
                        datetime.strptime(
                            f"{entry.get('date')} {entry.get('time')}",
                            '%Y-%m-%d %H:%M'
                        ),
                        timezone.get_current_timezone()
                    )
                    record_attendance(
                        employee=employee,
                        date=parsed_date,
                        timestamp=local_time,
                        is_time_in=(action == 'in'),
                        is_time_out=(action == 'out'),
                        att_source='manual'
                    )
                    affected_dates.add(parsed_date)
                except Exception as e:
                    return JsonResponse({"error": str(e)}, status=400)

            return JsonResponse({"message": "Entries saved successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator([permission_required('settings_personal_rest_days', 'read')], name='dispatch')
class EmployeeRestDayView(LoginRequiredMixin, View):

    def get(self, request):
        try:
            employee_id = request.GET.get('employee_id')
            rest_days   = EmployeeRestDay.objects.filter(
                employee__employee_id=employee_id
            ).select_related('employee').order_by('date') if employee_id else []
            return JsonResponse({
                "rest_days": [{"id": r.id, "date": r.date.strftime('%Y-%m-%d')} for r in rest_days]
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def post(self, request):
        try:
            data     = json.loads(request.body)
            emp_id   = data.get('employee_id')
            date_str = data.get('date')
            employee = Employee.objects.get(employee_id=emp_id)
            date     = datetime.strptime(date_str, '%Y-%m-%d').date()
            obj, created = EmployeeRestDay.objects.get_or_create(
                employee=employee, date=date,
                defaults={'created_by': request.user}
            )
            return JsonResponse({"status": "created" if created else "exists", "id": obj.id})
        except Employee.DoesNotExist:
            return JsonResponse({"error": "Employee not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request):
        try:
            data = json.loads(request.body)
            EmployeeRestDay.objects.filter(id=data.get('id')).delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator([permission_required('settings_personal_rest_days', 'read')], name='dispatch')
class RestDayManagementView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter  = get_dept_queryset_filter(request, dept_field_path='department')
        if dept_filter is None:
            return render(request, 'attendance/rest-days.html', {'dept_warning': True, 'employees': []})

        self_exclude = get_self_exclude(request)
        employees    = Employee.objects.filter(
            is_active=True, is_resigned=False, **dept_filter
        ).select_related('department')
        if self_exclude:
            employees = employees.exclude(pk=self_exclude)
        employees = employees.order_by('last_name', 'first_name')
        return render(request, 'attendance/rest-days.html', {'employees': employees})


@method_decorator([permission_required('approvals_missing_logs', 'read')], name='dispatch')
class MissingLogView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='employee__department')
        if dept_filter is None:
            return render(request, 'requests/missing_logs/ml-approval.html', {'dept_warning': True})

        missing_logs = list(
            MissingLog.objects
            .filter(status='PENDING', **dept_filter)
            .select_related('employee')
            .order_by('date', 'employee__last_name')
        )

        return render(request, 'requests/missing_logs/ml-approval.html', {
            'missing_logs': missing_logs,
        })

    def post(self, request):
        try:
            data    = json.loads(request.body)
            action  = data.get('action')
            log_id  = data.get('id')

            missing = MissingLog.objects.select_related('employee').get(id=log_id)

            if action == 'resolve':
                time_str    = data.get('time')
                assigned_dt = timezone.make_aware(
                    datetime.combine(
                        missing.date,
                        datetime.strptime(time_str, '%H:%M').time()
                    ),
                    timezone.get_current_timezone()
                )
                record_attendance(
                    employee=missing.employee,
                    date=missing.date,
                    timestamp=assigned_dt,
                    is_time_in=(missing.log_type == 'time_in'),
                    is_time_out=(missing.log_type == 'time_out'),
                    att_source='manual',
                )

                resolved_time = assigned_dt.time()
                if missing.log_type == 'time_in':
                    missing.time_in  = resolved_time
                else:
                    missing.time_out = resolved_time

                missing.status      = 'RESOLVED'
                missing.resolved_at = timezone.now()
                missing.resolved_by = request.user
                missing.save()
                return JsonResponse({'status': 'resolved'})

            elif action == 'dismiss':
                missing.status      = 'DISMISSED'
                missing.resolved_at = timezone.now()
                missing.resolved_by = request.user
                missing.save()
                return JsonResponse({'status': 'dismissed'})

            return JsonResponse({'error': 'Unknown action.'}, status=400)

        except MissingLog.DoesNotExist:
            return JsonResponse({'error': 'Record not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@method_decorator([permission_required('attendance', 'create')], name='dispatch')
class ManualOverwriteAttendanceView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            data        = json.loads(request.body)
            employee_id = data.get('employee_id')
            action      = data.get('log_action') 
            date_str    = data.get('date')
            time_str    = data.get('time')

            employee    = Employee.objects.get(employee_id=employee_id)
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            local_time  = timezone.make_aware(
                datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M'),
                timezone.get_current_timezone()
            )

            old_log = AttendanceLog.objects.filter(
                employee=employee,
                date=parsed_date,
                is_time_in=(action == 'in'),
                is_time_out=(action == 'out'),
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
                    log_type='time_in' if action == 'in' else 'time_out',
                )

            record_attendance(
                employee=employee,
                date=parsed_date,
                timestamp=local_time,
                is_time_in=(action == 'in'),
                is_time_out=(action == 'out'),
                att_source='manual'
            )

            return JsonResponse({"status": "overwritten"})

        except Employee.DoesNotExist:
            return JsonResponse({"error": "Employee not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)