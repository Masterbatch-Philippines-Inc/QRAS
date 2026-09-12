# from datetime import timedelta, datetime, date as date_cls
# from django.utils import timezone, timezone as tz
# from app.attendance.models import (
#     AttendanceLog, 
#     Holiday,
#     LeaveRequest,
#     AbsenceExcusal,
#     # UndertimeRequest,
#     Attendance, 
#     AttendanceStatus,
#     EmployeeRestDay,
#     MissingLog,
# )
# from app.employees.models import Employee, EmployeeSchedule
# from app.schedules.models import BREAK_HOURS
# from app.attendance.compute.core import compute_attendance_from_logs, _schedule_boundaries

# HALFDAY_LATE_MIN = 1.0


# # ─────────────────────────────────────────────────────────────────────────────
# #  TIME FORMATTER
# # ─────────────────────────────────────────────────────────────────────────────

# def format_hours_to_text(hours):
#     if hours is None:
#         return None
#     hours = float(hours)
#     h = int(hours)
#     m = int(round((hours - h) * 60))
#     if m == 60:
#         h += 1
#         m = 0
#     parts = []
#     if h > 0:
#         parts.append(f"{h}hr{'s' if h != 1 else ''}")
#     if m > 0:
#         parts.append(f"{m}min{'s' if m != 1 else ''}")
#     return ", ".join(parts) if parts else "0hrs"


# # ─────────────────────────────────────────────────────────────────────────────
# #  DISPLAY STATUS RESOLVER
# # ─────────────────────────────────────────────────────────────────────────────

# def resolve_display_status(s):
#     if s.status == 'RECORDED':
#         return 'RECORDED'
#     elif s.status == 'APPROVED':
#         return 'APPROVED'
#     elif s.status == 'REJECTED':
#         return 'REJECTED'
#     elif s.status == 'PENDING' and not s.is_completed and not s.is_undertime and not s.is_halfday:
#         return 'NOT YET'
#     return 'FOR APPROVAL'


# # ─────────────────────────────────────────────────────────────────────────────
# #  RECORD HELPERS
# # ─────────────────────────────────────────────────────────────────────────────

# def check_duplicate_log(employee, check_date, action):
#     logs = AttendanceLog.objects.filter(
#         employee=employee,
#         date=check_date,
#         is_replaced=False
#     ).order_by('timestamp')

#     if not logs.exists():
#         if action == "time_out":
#             yesterday = check_date - timedelta(days=1)
#             if _find_open_timein_date(employee, yesterday):
#                 return None
#             return {"status": "no_time_in"}
#         return None

#     last_log = logs.last()
#     if action == "time_in"  and last_log.is_time_in:  return {"status": "duplicate"}
#     if action == "time_out" and last_log.is_time_out: return {"status": "duplicate"}
#     return None


# def record_attendance(*, employee, date, timestamp, is_time_in, is_time_out, att_source="qr"):
#     log_date = date

#     # ── Crossing-midnight check ───────────────────────────────────────────
#     emp_schedule = EmployeeSchedule.objects.filter(
#         employee=employee, is_active=True
#     ).order_by('-effective_date').first()

#     if emp_schedule and emp_schedule.schedule.crosses_midnight and is_time_out:
#         tz       = timezone.get_current_timezone()
#         schedule = emp_schedule.schedule
#         yesterday = date - timedelta(days=1)
#         shift_start = timezone.make_aware(
#             datetime.combine(yesterday, schedule.shift_start), tz
#         )
#         shift_end = timezone.make_aware(
#             datetime.combine(date, schedule.shift_end), tz
#         )
#         if shift_start <= timestamp <= shift_end:
#             log_date = yesterday  # ← anchor to previous day

#     # ── existing logic below unchanged ───────────────────────────────────
#     if is_time_out:
#         found = _find_open_timein_date(employee, log_date)
#         if not found:
#             yesterday = log_date - timedelta(days=1)
#             found = _find_open_timein_date(employee, yesterday)
#         if found:
#             log_date = found

#     AttendanceLog.objects.create(
#         employee=employee,
#         date=log_date,
#         timestamp=timestamp,
#         is_time_in=is_time_in,
#         is_time_out=is_time_out,
#         att_source=att_source
#     )

#     result = compute_attendance_from_logs(employee, log_date)
#     _flag_past_missing_logs(employee, log_date)
#     return result


# def _find_open_timein_date(employee, check_date):
#     logs = AttendanceLog.objects.filter(
#         employee=employee,
#         date=check_date,
#         is_replaced=False
#     ).order_by('timestamp')
#     stack = None
#     for log in logs:
#         if log.is_time_in:
#             stack = log
#         elif log.is_time_out and stack:
#             stack = None
#     return check_date if stack else None

# # ─────────────────────────────────────────────────────────────────────────────
# #  ABSENCE LOGIC
# # ─────────────────────────────────────────────────────────────────────────────

# def get_absent_employees(check_date):
#     """
#     Single-date wrapper kept for backward compatibility with any other
#     callers outside the absence report. Delegates to the bulk function.
#     """
#     return get_absent_employees_range(check_date, check_date)


# def get_absent_employees_range(start_date, end_date, employee_qs=None):
#     """
#     Bulk-optimised absence query over a date range.

#     Executes 6 queries total regardless of employee count or range size:
#       1. Employees + related dept/position
#       2. Active EmployeeSchedule records (with schedule)
#       3. EmployeeRestDay overrides in range
#       4. Holiday dates in range
#       5. AttendanceLog (employee_id, date) pairs in range
#       6. AbsenceExcusal records in range (with leave_request)

#     Returns a flat list of dicts — same shape as the old get_absent_employees
#     but with an added 'date' key on every item.
#     """
#     if employee_qs is None:
#         employee_qs = Employee.objects.filter(is_active=True, is_resigned=False)

#     employees = list(
#         employee_qs.select_related('department', 'position')
#     )
#     if not employees:
#         return []

#     emp_pks = [e.pk for e in employees]

#     # ── 1. Active schedules — one per employee (most recent effective date) ──
#     raw_schedules = (
#         EmployeeSchedule.objects
#         .filter(employee_id__in=emp_pks, is_active=True, schedule__is_active=True)
#         .select_related('schedule')
#         .order_by('employee_id', '-effective_date')
#     )
#     # Keep only the first (most recent) per employee
#     emp_schedule_map = {}  # {employee_pk: EmployeeSchedule}
#     for es in raw_schedules:
#         if es.employee_id not in emp_schedule_map:
#             emp_schedule_map[es.employee_id] = es

#     # ── 2. Personal rest day overrides in range ──────────────────────────────
#     personal_rest_days = set(
#         EmployeeRestDay.objects
#         .filter(employee_id__in=emp_pks, date__range=(start_date, end_date))
#         .values_list('employee_id', 'date')
#     )

#     # ── 3. Holiday dates in range ────────────────────────────────────────────
#     holiday_dates = set(
#         Holiday.objects
#         .filter(date__range=(start_date, end_date))
#         .values_list('date', flat=True)
#     )

#     # ── 4. Attendance log presence — (employee_id, date) pairs ──────────────
#     logged_pairs = set(
#         AttendanceLog.objects
#         .filter(
#             employee_id__in=emp_pks,
#             date__range=(start_date, end_date),
#             is_replaced=False,
#         )
#         .values_list('employee_id', 'date')
#     )

#     # ── 5. Absence excusals in range ─────────────────────────────────────────
#     excusals_raw = (
#         AbsenceExcusal.objects
#         .filter(employee_id__in=emp_pks, date__range=(start_date, end_date))
#         .select_related('leave_request')
#     )
#     excusal_map = {}  # {(employee_pk, date): AbsenceExcusal}
#     for ex in excusals_raw:
#         excusal_map[(ex.employee_id, ex.date)] = ex

#     # ── Iterate and build results ────────────────────────────────────────────
#     absent = []
#     current = start_date
#     while current <= end_date:
#         is_holiday = current in holiday_dates

#         for emp in employees:
#             es = emp_schedule_map.get(emp.pk)
#             if not es:
#                 continue  # unscheduled — skip

#             schedule = es.schedule

#             # Schedule-level rest day
#             if current.weekday() in (schedule.rest_days or []):
#                 continue

#             # Personal rest day override
#             if (emp.pk, current) in personal_rest_days:
#                 continue

#             # Has a log for this date
#             if (emp.pk, current) in logged_pairs:
#                 continue

#             # Absent — check excusal
#             excusal = excusal_map.get((emp.pk, current))

#             absent.append({
#                 'date':        current,
#                 'employee':    emp,
#                 'schedule':    schedule,
#                 'is_holiday':  is_holiday,
#                 'is_excused':  excusal is not None,
#                 'excusal':     excusal,
#                 'leave_type':  excusal.leave_request.get_leave_type_display()
#                                if excusal and excusal.leave_request else None,
#             })

#         current += timedelta(days=1)

#     return absent


# # ─────────────────────────────────────────────────────────────────────────────
# #  LEAVE HELPERS
# # ─────────────────────────────────────────────────────────────────────────────

# def compute_leave_days(date_from, date_to, employee):
#     """
#     Counts working days between date_from and date_to.
#     Excludes rest days per employee schedule.
#     Returns total as float (0.5 per halfday — not used yet but ready).
#     Also returns list of rest day dates found in range.
#     """
#     emp_schedule = EmployeeSchedule.objects.filter(
#         employee=employee, is_active=True
#     ).order_by('-effective_date').first()

#     rest_days   = emp_schedule.schedule.rest_days if emp_schedule else [6]
#     total       = 0.0
#     rest_hits   = []
#     current     = date_from

#     while current <= date_to:
#         if current.weekday() in rest_days:
#             rest_hits.append(current)
#         else:
#             total += 1.0
#         current += timedelta(days=1)

#     return total, rest_hits


# def approve_leave(leave_request, decided_by):
#     """
#     Approves a leave request and handles side effects:
#     - undertime leave → auto-approve matching UndertimeRequest
#     - sick/vacation   → create AbsenceExcusal per date in range
#     """
#     leave_request.status     = 'APPROVED'
#     leave_request.decided_at = timezone.now()
#     leave_request.save()

#     # if leave_request.leave_type == 'undertime':
#     #     _handle_undertime_leave(leave_request, decided_by)
#     # else:
#     #     _handle_absence_excusal(leave_request, decided_by)


# def reject_leave(leave_request, remarks, decided_by):
#     """
#     Rejects a leave request — no side effects on attendance or absence.
#     """
#     leave_request.status     = 'REJECTED'
#     leave_request.decided_at = timezone.now()
#     leave_request.remarks    = remarks
#     leave_request.save()


# # ─────────────────────────────────────────────────────────────────────────────
# #  UNDERTIME CREDIT HOURS
# # ─────────────────────────────────────────────────────────────────────────────

# def _get_credited_for_undertime(att, is_halfday=False):
#     schedule = att.schedule
#     if not schedule:
#         return float(att.total_work_hours)

#     required          = min(float(schedule.required_hours), 8.0)
#     halfday_threshold = float(schedule.halfday_threshold)
#     start_aware, end_aware = _schedule_boundaries(schedule, att.date)

#     logs = AttendanceLog.objects.filter(
#         employee=att.employee,
#         date=att.date,
#         is_replaced=False
#     ).order_by('timestamp')

#     hours_within_shift = 0.0
#     actual_break       = 0.0
#     stack              = None
#     prev_out           = None

#     for log in logs:
#         if log.is_time_in:
#             if stack is None:
#                 if prev_out is not None:
#                     actual_break += (log.timestamp - prev_out).total_seconds() / 3600
#                 stack = log.timestamp
#         elif log.is_time_out and stack:
#             work_start = max(stack, start_aware)
#             work_end   = min(log.timestamp, end_aware)
#             duration   = (work_end - work_start).total_seconds() / 3600
#             if duration > 0:
#                 hours_within_shift += duration
#             prev_out = log.timestamp
#             stack    = None

#     from app.schedules.models import BREAK_HOURS
#     if prev_out is not None and actual_break > 0:
#         extra_deduction = max(0.0, BREAK_HOURS - actual_break)
#     elif is_halfday or hours_within_shift < halfday_threshold:
#         extra_deduction = 0.0
#     else:
#         extra_deduction = BREAK_HOURS

#     credited = max(0.0, hours_within_shift - extra_deduction)
#     return round(min(credited, required), 2)

# # ─────────────────────────────────────────────────────────────────────────────
# #  PRIVATE HANDLERS
# # ─────────────────────────────────────────────────────────────────────────────

# # def _handle_undertime_leave(leave_request, decided_by):
# #     """
# #     Finds UndertimeRequest for each date in range and auto-approves it
# #     with approval_source='leave'.
# #     """
# #     current = leave_request.date_from
# #     while current <= leave_request.date_to:
# #         ut = UndertimeRequest.objects.filter(
# #             attendance__employee=leave_request.employee,
# #             attendance__date=current,
# #             status='PENDING'
# #         ).select_related(
# #             'attendance__att_status',
# #             'attendance__schedule'
# #         ).first()

# #         if ut:
# #             ut.status          = 'APPROVED'
# #             ut.decided_at      = timezone.now()
# #             ut.approval_source = 'leave'
# #             ut.remarks         = f"Auto-approved via leave request #{leave_request.lf_number or leave_request.id}"
# #             ut.save()

# #             att      = ut.attendance
# #             schedule = att.schedule
# #             raw      = float(att.total_work_hours)
# #             credited = _get_credited_for_undertime(att)

# #             try:
# #                 s                = att.att_status
# #                 s.is_undertime   = True
# #                 s.status         = 'APPROVED'
# #                 s.credited_hours = round(credited, 2)
# #                 s.save(update_fields=['is_undertime', 'status', 'credited_hours'])
# #             except Exception:
# #                 pass

# #         current += timedelta(days=1)


# def _handle_absence_excusal(leave_request, decided_by):
#     """
#     Creates an AbsenceExcusal for each working day in the leave range.
#     Skips rest days.
#     """
#     emp_schedule = EmployeeSchedule.objects.filter(
#         employee=leave_request.employee, is_active=True
#     ).order_by('-effective_date').first()

#     rest_days = emp_schedule.schedule.rest_days if emp_schedule else [6]
#     current   = leave_request.date_from

#     while current <= leave_request.date_to:
#         if current.weekday() not in rest_days:
#             AbsenceExcusal.objects.get_or_create(
#                 employee=leave_request.employee,
#                 date=current,
#                 defaults={
#                     'leave_request': leave_request,
#                     'excused_by':    decided_by,
#                     'note':          f"{leave_request.get_leave_type_display()} — {leave_request.reason}",
#                 }
#             )
#         current += timedelta(days=1)

# # ─────────────────────────────────────────────────────────────────────────────
# #  HALDAY CREDITS
# # ─────────────────────────────────────────────────────────────────────────────

# def _compute_halfday_credited(attendance, threshold, halfday_type='am'):
#     schedule = attendance.schedule
#     if not schedule:
#         return round(min(float(attendance.total_work_hours), threshold), 2)

#     start_aware, end_aware = _schedule_boundaries(schedule, attendance.date)
#     from datetime import timedelta

#     # define the window for the relevant half only
#     if halfday_type == 'am':
#         window_start = start_aware
#         window_end   = start_aware + timedelta(hours=float(threshold))
#     else:  # pm
#         window_start = start_aware + timedelta(hours=float(threshold) + BREAK_HOURS)
#         window_end   = end_aware

#     logs = AttendanceLog.objects.filter(
#         employee=attendance.employee,
#         date=attendance.date,
#         is_replaced=False
#     ).order_by('timestamp')

#     hours_in_half = 0.0
#     stack = None
#     for log in logs:
#         if log.is_time_in:
#             if stack is None:
#                 stack = log.timestamp
#         elif log.is_time_out and stack:
#             work_start = max(stack, window_start)   # ← cap to half window
#             work_end   = min(log.timestamp, window_end)
#             duration   = (work_end - work_start).total_seconds() / 3600
#             if duration > 0:
#                 hours_in_half += duration
#             stack = None

#     return round(min(hours_in_half, threshold), 2)

# # ─────────────────────────────────────────────────────────────────────────────
# #  MISSING LOG DETECTION
# # ─────────────────────────────────────────────────────────────────────────────

# def detect_and_sync_missing_logs(check_date):
#     """
#     Scans all active, scheduled employees' logs for check_date.
#     Creates a MissingLog record for any incomplete attendance:
#       - has time-in  but no time-out → log_type = 'time_out'
#       - has time-out but no time-in  → log_type = 'time_in'
#     Skips rest days and unscheduled employees.
#     Never overwrites an existing record (RESOLVED / DISMISSED stay intact).
#     """

#     """
#     DEV NOTICE!!!!
    
#     [DISABLED] MissingLog queue creation is replaced by the inline has_missing_log
#     flag on AttendanceStatus. Missing log detection now happens automatically via
#     _flag_past_missing_logs() in record_attendance(), and is set per-record in
#     compute_attendance_from_logs(). The MissingLog table and approval views are
#     kept intact and can be re-enabled without data loss.
#     """
    
#     pass
#     # employees = Employee.objects.filter(is_active=True, is_resigned=False)

#     # for emp in employees:
#     #     emp_schedule = EmployeeSchedule.objects.filter(
#     #         employee=emp, is_active=True, schedule__is_active=True
#     #     ).order_by('-effective_date').first()

#     #     if not emp_schedule:
#     #         continue

#     #     schedule = emp_schedule.schedule
#     #     if check_date.weekday() in (schedule.rest_days or []):
#     #         continue
#     #     if EmployeeRestDay.objects.filter(employee=emp, date=check_date).exists():
#     #         continue

#     #     logs = AttendanceLog.objects.filter(
#     #         employee=emp, date=check_date, is_replaced=False
#     #     ).order_by('timestamp')

#     #     if not logs.exists():
#     #         continue  # absent — handled separately

#     #     has_time_in  = logs.filter(is_time_in=True).exists()
#     #     next_day_logs = AttendanceLog.objects.filter(
#     #         employee=emp, date=check_date + timedelta(days=1), is_replaced=False
#     #     )
#     #     has_time_out = logs.filter(is_time_out=True).exists() or \
#     #                 next_day_logs.filter(is_time_out=True).exists()

#     #     first_in  = logs.filter(is_time_in=True).first()
#     #     last_out = logs.filter(is_time_out=True).last() or \
#     #        next_day_logs.filter(is_time_out=True).first()
#     #     time_in_val  = timezone.localtime(first_in.timestamp).time()  if first_in  else None
#     #     time_out_val = timezone.localtime(last_out.timestamp).time()  if last_out  else None

#     #     if has_time_in and not has_time_out:
#     #         MissingLog.objects.get_or_create(
#     #             employee=emp,
#     #             date=check_date,
#     #             log_type='time_out',
#     #             defaults={'time_in': time_in_val, 'time_out': None},
#     #         )
#     #     elif has_time_out and not has_time_in:
#     #         MissingLog.objects.get_or_create(
#     #             employee=emp,
#     #             date=check_date,
#     #             log_type='time_in',
#     #             defaults={'time_in': None, 'time_out': time_out_val},
#     #         )

# def _flag_past_missing_logs(employee, current_date, lookback_start=None):
#     """
#     Called after every record_attendance() to scan past Attendance records for
#     this employee and update has_missing_log on AttendanceStatus.

#     Logic:
#       - Looks back from today (exclusive) to lookback_start.
#         Defaults to 30 days back if not provided.
#       - A day is flagged if it has at least one log but only one side:
#           time_in  present, time_out missing → has_missing_log = True
#           time_out present, time_in  missing → has_missing_log = True
#       - A day is un-flagged if it now has both sides or no logs at all.
#       - Only flags a date if a later attendance log exists — proof the
#         employee returned and the gap is genuinely incomplete.
#       - Skips days with no AttendanceStatus (edge case — should not happen).
#       - Does NOT touch MissingLog records (those are handled by the disabled
#         detect_and_sync_missing_logs queue and can be re-enabled independently).
#     """
#     today = date_cls.today()
#     if lookback_start is None:
#         lookback_start = today - timedelta(days=30)

#     past_records = Attendance.objects.filter(
#         employee=employee,
#         date__gte=lookback_start,
#         date__lt=today,
#     )

#     for att in past_records:
#         logs = AttendanceLog.objects.filter(
#             employee=employee,
#             date=att.date,
#             is_replaced=False,
#         )

#         if not logs.exists():
#             continue

#         has_in  = logs.filter(is_time_in=True).exists()
#         has_out = logs.filter(is_time_out=True).exists()
#         is_incomplete = (has_in and not has_out) or (has_out and not has_in)

#         if is_incomplete:
#             has_later_log = AttendanceLog.objects.filter(
#                 employee=employee,
#                 date__gt=att.date,
#                 is_replaced=False,
#             ).exists()
#             should_flag = has_later_log
#         else:
#             should_flag = False

#         try:
#             s = att.att_status
#         except AttendanceStatus.DoesNotExist:
#             continue

#         if s.has_missing_log != should_flag:
#             s.has_missing_log = should_flag
#             s.save(update_fields=['has_missing_log'])

