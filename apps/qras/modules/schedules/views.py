import json
from datetime import date, datetime as dt

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.db.models import Prefetch, Q

from apps.qras.models.employee import Employee, EmployeeSchedule
from apps.qras.models.attendance import (
    Attendance, 
    OvertimeRequest,
)
from apps.qras.models.schedules import (
    ScheduleRecomputeEvent, 
)
from apps.qras.models.schedules import ShiftSchedule, ScheduleActivityLog
from apps.qras.modules.attendance.computation import compute_attendance_from_logs
from apps.qras.modules.auth.decorators import permission_required
from apps.qras.modules.auth.helpers import get_dept_queryset_filter, get_self_exclude
from django.utils.decorators import method_decorator

from datetime import datetime, timedelta
from apps.qras.modules.attendance.helpers import get_absent_employees_range
from datetime import date as date_type


# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULE LIST
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('schedules', 'read')], name='dispatch')
class ScheduleListView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='department')
        if dept_filter is None:
            return render(request, 'pages/schedule/with_scheds.django', {'dept_warning': True})

        self_exclude = get_self_exclude(request)


        is_admin = request.user.role and request.user.role.name == 'Administrator'
        if is_admin:
            schedules = ShiftSchedule.objects.all().order_by('name')
        else:
            schedules = ShiftSchedule.objects.filter(
                Q(is_global=True) |
                Q(created_by__department=request.user.department)
            ).distinct().order_by('name')

        employees = Employee.objects.filter(
            is_active=True, is_resigned=False, **dept_filter
        ).prefetch_related(
            Prefetch(
                'schedules',
                queryset=EmployeeSchedule.objects.filter(
                    is_active=True
                ).select_related('schedule'),
                to_attr='active_schedules'
            )
        ).order_by('last_name')
        if self_exclude:
            employees = employees.exclude(pk=self_exclude)

        if is_admin:
            active_schedules = ShiftSchedule.objects.filter(is_active=True).order_by('name')
        else:
            active_schedules = ShiftSchedule.objects.filter(
                is_active=True
            ).filter(
                Q(is_global=True) | Q(created_by__department=request.user.department)
            ).distinct().order_by('name')

        return render(request, 'pages/schedule/with_scheds.django', {
            'schedules':        schedules,
            'active_schedules': active_schedules,
            'employees':        employees,
            'is_admin':         is_admin,
        })

# ─────────────────────────────────────────────────────────────────────────────
#  UNSCHEDULED RECORDS
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('unscheduled', 'read')], name='dispatch')
class UnscheduledRecordsView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='department')
        if dept_filter is None:
            return render(request, 'pages/schedule/no_scheds.django', {'dept_warning': True})

        self_exclude = get_self_exclude(request)

        unscheduled_emps = Employee.objects.filter(
            is_active=True,
            is_resigned=False,
            attendance__isnull=False,
            **dept_filter
        ).exclude(schedules__is_active=True).distinct().order_by('last_name')
        if self_exclude:
            unscheduled_emps = unscheduled_emps.exclude(pk=self_exclude)

        employees = [
            {
                'employee':         emp,
                'attendance_count': Attendance.objects.filter(employee=emp).count(),
            }
            for emp in unscheduled_emps
        ]

        is_admin = request.user.role and request.user.role.name == 'Administrator'

        if is_admin:
            schedules = ShiftSchedule.objects.filter(is_active=True).order_by('name')
        else:
            schedules = ShiftSchedule.objects.filter(is_active=True).filter(
                Q(is_global=True) | Q(created_by__department=request.user.department)
            ).distinct().order_by('name')

        return render(request, 'pages/schedule/no_scheds.django', {
            'employees': employees,
            'schedules': schedules,
        })

# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULE ASSIGN + RECOMPUTE
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('schedules', 'create')], name='dispatch')
class ScheduleAssignRecomputeView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            data        = json.loads(request.body)
            employee_id = data.get('employee_id')
            schedule_id = data.get('schedule_id')

            employee = Employee.objects.get(employee_id=employee_id)
            schedule = ShiftSchedule.objects.get(id=schedule_id)
            
            # Step 1: capture previous before deactivating
            prev = EmployeeSchedule.objects.filter(
                employee=employee, is_active=True
            ).select_related('schedule').order_by('-effective_date').first()
            prev_schedule = prev.schedule if prev else None

            # Step 2: deactivate all existing schedules first
            EmployeeSchedule.objects.filter(
                employee=employee
            ).update(is_active=False)

            # Step 3: Create or update the new one
            EmployeeSchedule.objects.update_or_create(
                employee=employee,
                schedule=schedule,
                defaults={'is_active': True, 'effective_date': date.today()}
            )

            ScheduleActivityLog.objects.create(
                employee=employee,
                assigned_schedule=schedule,
                previous_schedule=prev_schedule,
                acted_by=request.user,
            )

            recompute_scope = data.get('recompute_scope', 'all')
            today           = date.today()
            all_dates       = list(Attendance.objects.filter(employee=employee).values_list('date', flat=True))

            if recompute_scope == 'single_date':
                raw = data.get('recompute_date')
                try:
                    target = date.fromisoformat(raw)
                except (TypeError, ValueError):
                    return JsonResponse({"error": "Invalid date for single_date scope."}, status=400)
                dates = [d for d in all_dates if d == target]
                scope_description = f"single_date: {target}"

            elif recompute_scope == 'date_range':
                raw_from = data.get('recompute_from')
                raw_to   = data.get('recompute_to')
                try:
                    d_from = date.fromisoformat(raw_from)
                    d_to   = date.fromisoformat(raw_to)
                except (TypeError, ValueError):
                    return JsonResponse({"error": "Invalid date range."}, status=400)
                if d_from > d_to:
                    return JsonResponse({"error": "Start date must be before end date."}, status=400)
                dates = [d for d in all_dates if d_from <= d <= d_to]
                scope_description = f"date_range: {d_from} to {d_to}"

            elif recompute_scope == 'from_today':
                # legacy — kept for backward compat, no longer surfaced in UI
                dates = [d for d in all_dates if d >= today]
                scope_description = f"from_today: {today}"

            else:  # 'all'
                dates = all_dates
                scope_description = "all"

            if not dates:
                return JsonResponse({
                    "status":        "assigned",
                    "schedule_name": schedule.name,
                    "recomputed":    0,
                    "outside_logs":  0,
                    "info":          "Schedule assigned. No matching attendance records found for the selected scope — other records were left untouched.",
                })

            from app.attendance.models import (
                AttendanceLog, ScheduleRecomputeEvent, ScheduleRecomputeDetail
            )

            outside_logs_count = 0

            event = ScheduleRecomputeEvent.objects.create(
                employee=employee,
                old_schedule=prev_schedule,
                new_schedule=schedule,
                recomputed_by=request.user,
                scope_description=scope_description,
            )

            for work_date in dates:
                # --- snapshot BEFORE ---
                before_att = Attendance.objects.filter(employee=employee, date=work_date).first()
                before_credited = before_att.att_status.credited_hours if before_att and hasattr(before_att, 'att_status') else 0

                before_logs = AttendanceLog.objects.filter(
                    employee=employee, date=work_date, is_replaced=False
                ).order_by('timestamp')
                before_ti  = next((l.timestamp for l in before_logs if l.is_time_in),  None)
                before_to  = next((l.timestamp for l in before_logs if l.is_time_out), None)

                # --- recompute ---
                att = compute_attendance_from_logs(
                    employee, work_date,
                    schedule_override=schedule,
                    skip_auto_approve=False
                )
                ot = OvertimeRequest.objects.filter(attendance=att, status='APPROVED').first()
                if ot:
                    att.overtime_hours = ot.ot_hours
                    att.save(update_fields=['overtime_hours'])
                if att and float(att.total_work_hours) > 0 and float(att.att_status.credited_hours) == 0:
                    outside_logs_count += 1

                # --- snapshot AFTER ---
                after_logs = AttendanceLog.objects.filter(
                    employee=employee, date=work_date, is_replaced=False
                ).order_by('timestamp')
                after_ti  = next((l.timestamp for l in after_logs if l.is_time_in),  None)
                after_to  = next((l.timestamp for l in after_logs if l.is_time_out), None)
                after_credited = att.att_status.credited_hours if att and hasattr(att, 'att_status') else 0

                ScheduleRecomputeDetail.objects.create(
                    event=event,
                    date=work_date,
                    before_time_in=before_ti,
                    before_time_out=before_to,
                    before_credited_hrs=before_credited,
                    after_time_in=after_ti,
                    after_time_out=after_to,
                    after_credited_hrs=after_credited,
                )

            return JsonResponse({
                "status":        "assigned",
                "schedule_name": schedule.name,
                "recomputed":    len(dates),
                "outside_logs":  outside_logs_count,
                "info":          None,
            })

        except Employee.DoesNotExist:
            return JsonResponse({"error": "Employee not found."}, status=404)
        except ShiftSchedule.DoesNotExist:
            return JsonResponse({"error": "Schedule not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULE SAVE
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('schedules', 'create')], name='dispatch')
class ScheduleSaveView(LoginRequiredMixin, View):

    def post(self, request):
        '''
        Important Note: 
        
        rest_days field inside the model is a list data type
        so the records to be save will be numbers only.
        
        Monday is [0] and Sunday is [6]
        '''
        try:
            data        = json.loads(request.body)
            schedule_id = data.get('id')

            # Duplicate name check — system-wide, case-insensitive
            is_admin = request.user.role and request.user.role.name == 'Administrator'
            name = data.get('name', '').strip()
            dup_qs = ShiftSchedule.objects.filter(name__iexact=name)
            if schedule_id:
                dup_qs = dup_qs.exclude(id=schedule_id)
            if dup_qs.exists():
                return JsonResponse({"error": f'A schedule named "{name}" already exists. Please choose a different name.'}, status=400)

            fields = {
                'name':              data.get('name'),
                'shift_start':       dt.strptime(data.get('shift_start'), '%H:%M').time(),
                'shift_end':         dt.strptime(data.get('shift_end'),   '%H:%M').time(),
                'halfday_threshold': 4.0,
                'crosses_midnight':  data.get('crosses_midnight', False),
                'is_active':         data.get('is_active', True),
                'rest_days':         data.get('rest_days', []),
                'specific_dates':    data.get('specific_dates', []),
                'is_global':         data.get('is_global', False) if is_admin else False,
            }
            if schedule_id:
                ShiftSchedule.objects.filter(id=schedule_id).update(**fields)
                schedule = ShiftSchedule.objects.get(id=schedule_id)
                if schedule.created_by is None:
                    schedule.created_by = request.user
                    schedule.save(update_fields=['created_by'])
            else:
                schedule = ShiftSchedule.objects.create(**fields, created_by=request.user)

            return JsonResponse({
                "status":         "saved",
                "id":             schedule.id,
                "name":           schedule.name,
                "required_hours": schedule.required_hours,
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULE SOFT DELETE
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('schedules', 'delete')], name='dispatch')
class ScheduleSoftDeleteView(LoginRequiredMixin, View):

    def delete(self, request, schedule_id):
        try:
            schedule = ShiftSchedule.objects.get(id=schedule_id)
            affected = EmployeeSchedule.objects.filter(schedule=schedule, is_active=True).count()
            schedule.is_active  = False
            schedule.save(update_fields=['is_active'])

            return JsonResponse({
                "status":   "deleted",
                "affected": affected,
                "message":  f"{affected} employee(s) are still assigned to this schedule."
                            if affected else "No employees were affected.",
            })
        except ShiftSchedule.DoesNotExist:
            return JsonResponse({"error": "Schedule not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator([permission_required('schedules', 'update')], name='dispatch')
class ScheduleRestoreView(LoginRequiredMixin, View):

    def post(self, request, schedule_id):
        try:
            schedule            = ShiftSchedule.objects.get(id=schedule_id)
            schedule.is_active  = True
            schedule.save(update_fields=['is_active'])
            return JsonResponse({"status": "restored", "message": f"'{schedule.name}' has been restored."})
        except ShiftSchedule.DoesNotExist:
            return JsonResponse({"error": "Schedule not found."}, status=404)

# ─────────────────────────────────────────────────────────────────────────────
#  SCHEDULE ASSIGNATION
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('schedules', 'update')], name='dispatch')
class ScheduleAssignView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            data         = json.loads(request.body)
            schedule_id  = data.get('schedule_id')
            employee_ids = data.get('employee_ids', [])

            schedule  = ShiftSchedule.objects.get(id=schedule_id)
            employees = Employee.objects.filter(employee_id__in=employee_ids)

            for employee in employees:
                # Step 1: capture previous before deactivating
                prev = EmployeeSchedule.objects.filter(
                    employee=employee, is_active=True
                ).select_related('schedule').order_by('-effective_date').first()
                prev_schedule = prev.schedule if prev else None

                # Step 2: deactivate all existing schedules first
                EmployeeSchedule.objects.filter(
                    employee=employee
                ).update(is_active=False)

                # Step 3: Create or update the new one
                EmployeeSchedule.objects.update_or_create(
                    employee=employee,
                    schedule=schedule,
                    defaults={'is_active': True, 'effective_date': date.today()}
                )

                ScheduleActivityLog.objects.create(
                    employee=employee,
                    assigned_schedule=schedule,
                    previous_schedule=prev_schedule,
                    acted_by=request.user,
                )

            return JsonResponse({
                "status":        "assigned",
                "updated":       employees.count(),
                "schedule_name": schedule.name,
            })
        except ShiftSchedule.DoesNotExist:
            return JsonResponse({"error": "Schedule not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator([permission_required('schedules', 'update')], name='dispatch')
class ScheduleUnassignView(LoginRequiredMixin, View):

    def get(self, request):
        try:
            employee_id = request.GET.get('employee_id')
            employee    = Employee.objects.get(employee_id=employee_id)
            emp_sched   = EmployeeSchedule.objects.filter(
                employee=employee, is_active=True
            ).select_related('schedule').order_by('-effective_date').first()

            if not emp_sched:
                return JsonResponse({"error": "Employee has no active schedule."}, status=404)

            return JsonResponse({
                "employee_name":  f"{employee.last_name}, {employee.first_name}",
                "schedule_name":  emp_sched.schedule.name,
                "employee_id":    employee.employee_id,
            })
        except Employee.DoesNotExist:
            return JsonResponse({"error": "Employee not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def post(self, request):
        try:
            data        = json.loads(request.body)
            employee_id = data.get('employee_id')
            employee    = Employee.objects.get(employee_id=employee_id)

            updated = EmployeeSchedule.objects.filter(
                employee=employee, is_active=True
            ).update(is_active=False)

            if not updated:
                return JsonResponse({"error": "No active schedule to unassign."}, status=400)

            return JsonResponse({
                "status":  "unassigned",
                "message": f"Schedule unassigned from {employee.last_name}, {employee.first_name}.",
            })
        except Employee.DoesNotExist:
            return JsonResponse({"error": "Employee not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

# ─────────────────────────────────────────────────────────────────────────────
#  ABSENCES LOGS
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator([permission_required('absences', 'read')], name='dispatch')
class AbsenceReportView(LoginRequiredMixin, View):

    def get(self, request):
        start_str   = request.GET.get('start_date')
        end_str     = request.GET.get('end_date')
        employee_id = request.GET.get('employee_id', '').strip()
        absent_list = []
        start_date  = None
        end_date    = None
        selected_employee = None

        dept_filter = get_dept_queryset_filter(request, dept_field_path='department')
        if dept_filter is None:
            return render(request, 'pages/schedule/absents.django', {'dept_warning': True})

        # Build employee list for the dropdown (dept-scoped)
        employees = Employee.objects.filter(
            is_active=True, is_resigned=False, **dept_filter
        ).order_by('last_name', 'first_name')

        # Resolve selected employee
        if employee_id:
            try:
                selected_employee = employees.get(employee_id=employee_id)
            except Employee.DoesNotExist:
                selected_employee = None

        has_query = bool(start_str or end_str or employee_id)

        if has_query:
            today = date_type.today()

            if start_str and end_str:
                try:
                    start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                    end_date   = datetime.strptime(end_str,   '%Y-%m-%d').date()
                except ValueError:
                    start_date = end_date = None
            else:
                start_date = today.replace(day=1)
                end_date   = today

            if start_date and end_date:
                # Scope the employee queryset before passing to the bulk helper
                scoped_qs = employees  # already dept-filtered above
                if selected_employee:
                    scoped_qs = employees.filter(pk=selected_employee.pk)

                absent_list = get_absent_employees_range(
                    start_date, end_date, employee_qs=scoped_qs
                )

        return render(request, 'pages/schedule/absents.django', {
            'absent_list':        absent_list,
            'start_date':         start_date if start_date else '',
            'end_date':           end_date   if end_date   else '',
            'employees':          employees,
            'selected_employee':  selected_employee,
            'today':              date_type.today().isoformat(),
            'has_query':          has_query,
        })


@method_decorator([permission_required('schedules', 'read')], name='dispatch')
class RecomputeLogView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='department')
        if dept_filter is None:
            return render(request, 'pages/schedule/recomputes.django', {'dept_warning': True})

        self_exclude = get_self_exclude(request)

        qs = ScheduleRecomputeEvent.objects.select_related(
            'employee', 'employee__department',
            'old_schedule', 'new_schedule', 'recomputed_by'
        ).prefetch_related('details')

        if dept_filter:
            qs = qs.filter(employee__department=dept_filter.get('department'))

        if self_exclude:
            qs = qs.exclude(employee__pk=self_exclude)

        return render(request, 'pages/schedule/recomputes.django', {'events': qs})