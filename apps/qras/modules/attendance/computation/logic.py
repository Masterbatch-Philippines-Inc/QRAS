_ND_START = time(22, 0)  # 10:00 PM — PH Labor Code Art. 86
_ND_END   = time(6,  0)  # 06:00 AM

from django.utils import timezone
from datetime import date, datetime, time, timedelta

from qras.models.employee import (
    EmployeeGroupMembership
)
from qras.models.management import BREAK_HOURS
from qras.models.attendance import (
    Attendance, 
    AttendanceStatus,
    AttendanceLog,
    Holiday,
    OvertimeRequest
)
from qras.models.employee import EmployeeSchedule

from .steps.pairing    import pair_logs
from .steps.hours      import compute_hours
from .steps.late       import compute_late
from .steps.halfday    import compute_halfday
from .steps.completion import compute_completion
from .steps.undertime  import compute_undertime
from .steps.overtime   import compute_overtime, _split_24hr_schedule
from .steps.credited   import compute_credited


def _get_schedule(employee, work_date, override=None):
    if override:
        return override
    active_scheds = EmployeeSchedule.objects.filter(
        employee=employee, is_active=True
    ).select_related('schedule')
    # 1. Date-specific schedule takes priority
    work_date_str = work_date.isoformat()
    for es in active_scheds:
        if es.schedule and work_date_str in (es.schedule.specific_dates or []):
            return es.schedule
    # 2. Fall back: most recent schedule effective on or before work_date
    emp_schedule = active_scheds.filter(
        effective_date__lte=work_date
    ).order_by('-effective_date').first()
    return emp_schedule.schedule if emp_schedule else None


def _schedule_boundaries(schedule, work_date):
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(
        datetime.combine(work_date, schedule.shift_start), tz
    )
    end_date = work_date + timedelta(days=1) if schedule.crosses_midnight else work_date
    end_dt   = timezone.make_aware(
        datetime.combine(end_date, schedule.shift_end), tz
    )
    if end_dt <= start_dt:
        end_dt = timezone.make_aware(
            datetime.combine(work_date + timedelta(days=1), schedule.shift_end), tz
        )
    return start_dt, end_dt


def compute_attendance_from_logs(employee, work_date, schedule_override=None, skip_auto_approve=False):

    # ── Fetch logs ────────────────────────────────────────────────────────
    logs = AttendanceLog.objects.filter(
        employee=employee,
        date=work_date,
        is_replaced=False
    ).order_by('timestamp')

    # ── Schedule setup ────────────────────────────────────────────────────
    schedule     = _get_schedule(employee, work_date, schedule_override)
    has_schedule = schedule is not None

    if has_schedule:
        required_hours    = min(float(schedule.required_hours), 8.0)
        halfday_threshold = float(schedule.halfday_threshold)
        start_aware, end_aware = _schedule_boundaries(schedule, work_date)
    else:
        required_hours    = float(getattr(employee, 'required_work_hours', 8))
        halfday_threshold = required_hours / 2
        start_aware = end_aware = None

    is_long_shift = has_schedule and float(schedule.required_hours) > 8.0
    is_24hr_shift = has_schedule and float(schedule.required_hours) >= 22.0

    # ── Step 1: Pair logs ─────────────────────────────────────────────────
    pairing       = pair_logs(logs)
    pairs         = pairing.pairs
    stack         = pairing.stack
    first_time_in = pairing.first_time_in
    has_time_out  = len(pairs) > 0
    is_present    = len(pairs) > 0 or stack is not None

    # ── Step 2: Hours ─────────────────────────────────────────────────────
    hours = compute_hours(
        pairs=pairs,
        has_schedule=has_schedule,
        is_long_shift=is_long_shift,
        is_24hr_shift=is_24hr_shift,
        start_aware=start_aware,
        end_aware=end_aware,
        halfday_threshold=halfday_threshold,
        schedule=schedule,
        work_date=work_date,
    )

    # ── Step 3: Late ──────────────────────────────────────────────────────
    late = compute_late(
        first_time_in=first_time_in,
        start_aware=start_aware,
        halfday_threshold=halfday_threshold,
        required_hours=required_hours,
        has_schedule=has_schedule,
    )

    # ── Step 4: Halfday ───────────────────────────────────────────────────
    halfday = compute_halfday(
        hours=hours,
        late=late,
        halfday_threshold=halfday_threshold,
        is_present=is_present,
        has_schedule=has_schedule,
        has_time_out=has_time_out,
    )

    # ── Step 5: Completion ────────────────────────────────────────────────
    completion = compute_completion(
        pairs=pairs,
        hours=hours,
        late=late,
        has_schedule=has_schedule,
        is_long_shift=is_long_shift,
        is_24hr_shift=is_24hr_shift,
        end_aware=end_aware,
        required_hours=required_hours,
    )

    # ── Step 6: Undertime ─────────────────────────────────────────────────
    undertime = compute_undertime(
        pairs=pairs,
        hours=hours,
        completion=completion,
        halfday=halfday,
        has_schedule=has_schedule,
        is_long_shift=is_long_shift,
        is_24hr_shift=is_24hr_shift,
        start_aware=start_aware,
        end_aware=end_aware,
        required_hours=required_hours,
        is_present=is_present,
        halfday_threshold=halfday_threshold,
    )

    # ── Step 7: Overtime ──────────────────────────────────────────────────
    overtime = compute_overtime(
        pairs=pairs,
        hours=hours,
        has_schedule=has_schedule,
        is_long_shift=is_long_shift,
        is_24hr_shift=is_24hr_shift,
        start_aware=start_aware,
        end_aware=end_aware,
        required_hours=required_hours,
        schedule=schedule,
        work_date=work_date,
    )

    # ── Step 8: 24hr sub-window credited ─────────────────────────────────
    sub1_raw = sub2_raw = 0.0
    if is_24hr_shift and pairs:
        (sub1_s, sub1_e), (sub2_s, sub2_e) = _split_24hr_schedule(schedule, work_date)
        def _hours_in_window(start, end):
            total = 0.0
            for inn, out in pairs:
                ws = max(inn, start)
                we = min(out, end)
                d  = (we - ws).total_seconds() / 3600
                if d > 0:
                    total += d
            return total
        sub1_raw = max(0.0, _hours_in_window(sub1_s, sub1_e) - BREAK_HOURS)
        sub2_raw = max(0.0, _hours_in_window(sub2_s, sub2_e) - BREAK_HOURS)

    # ── Step 9: Credited ──────────────────────────────────────────────────
    credited = compute_credited(
        hours=hours,
        late=late,
        halfday=halfday,
        undertime=undertime,
        completion=completion,
        halfday_threshold=halfday_threshold,
        required_hours=required_hours,
        is_24hr_shift=is_24hr_shift,
        sub1_raw=sub1_raw,
        sub2_raw=sub2_raw,
    )

    # ── Late cleanup for halfday-by-late + completed ───────────────────────
    is_late    = late.is_late
    late_hours = late.late_hours
    # if halfday.is_halfday and halfday.is_halfday_by_late and completion.is_completed:
    #     is_late    = False
    #     late_hours = 0.0

    # ── Sunday / Holiday / Night diff ─────────────────────────────────────
    is_sunday = work_date.weekday() == 6
    if not is_sunday and pairs:
        for inn, out in pairs:
            if timezone.localtime(inn).date().weekday() == 6 or \
               timezone.localtime(out).date().weekday() == 6:
                is_sunday = True
                break

    _holiday            = Holiday.objects.filter(date=work_date).first()
    is_regular_holiday  = _holiday is not None and _holiday.type == 'regular'
    is_special_holiday  = _holiday is not None and _holiday.type == 'special'
    has_night_diff = _check_night_diff(pairs, schedule) if has_schedule else False

    # ── total_work_display adjustment for halfday ─────────────────────────
    total_work_display = (
        hours.actual_hours_worked if halfday.is_halfday
        else hours.total_work_display
    )

    # ── Persist Attendance ────────────────────────────────────────────────
    # Preserve approved OT hours if an approved OvertimeRequest exists
    existing_approved_ot = OvertimeRequest.objects.filter(
        attendance__employee=employee,
        attendance__date=work_date,
        status='APPROVED'
    ).first()
    preserved_ot_hours = float(existing_approved_ot.ot_hours) if existing_approved_ot else 0.0

    attendance, _ = Attendance.objects.update_or_create(
        employee=employee,
        date=work_date,
        defaults={
            "schedule":         schedule,
            "total_work_hours": round(total_work_display, 2),
            "overtime_hours":   preserved_ot_hours,
            "undertime_hours":  round(undertime.undertime, 2),
            "late_hours":       late_hours,
        }
    )

    # ── Persist AttendanceStatus ──────────────────────────────────────────
    att_status, created = AttendanceStatus.objects.get_or_create(
        attendance=attendance,
        defaults={"status": "PENDING"}
    )

    att_status.is_present     = is_present
    att_status.is_late        = is_late
    att_status.is_halfday     = halfday.is_halfday
    att_status.is_completed   = completion.is_completed
    att_status.is_overtime    = False
    att_status.is_undertime   = undertime.is_undertime
    att_status.has_night_diff = has_night_diff
    att_status.is_sunday      = is_sunday
    att_status.is_regular_holiday = is_regular_holiday
    att_status.is_special_holiday = is_special_holiday
    att_status.is_absent      = not is_present

    # ── Status logic ──────────────────────────────────────────────────────
    if not skip_auto_approve:
        if credited.disciplinary_action:
            att_status.status    = "REJECTED"
            att_status.is_absent = True
            att_status.credited_hours = 0.0
        elif is_present and has_time_out:
            att_status.status         = "RECORDED"
            att_status.credited_hours = credited.credited
        else:
            att_status.status         = "PENDING"
            att_status.credited_hours = 0.0  # ← skip credited when PENDING
    elif created:
        att_status.status         = "PENDING"
        att_status.credited_hours = 0.0

    # ── Absent guard — clear halfday/undertime if marked absent ──────────
    if att_status.is_absent:
        att_status.is_halfday    = False
        att_status.is_undertime  = False
        attendance.undertime_hours = 0.0
        attendance.save(update_fields=['undertime_hours'])

    att_status.save()

    # ── OT handling ───────────────────────────────────────────────────────────
    total_ot = round(overtime.overtime + overtime.pre_overtime, 2)

    if total_ot > 0:
        is_exempt = EmployeeGroupMembership.objects.filter(
            employee=employee, group__ot_filing_exempted=True
        ).exists()

        if is_exempt:
            # Auto-credit combined OT immediately — no approval needed
            attendance.overtime_hours = total_ot
            attendance.save(update_fields=['overtime_hours'])
            att_status.is_overtime = True
            att_status.save(update_fields=['is_overtime'])
        else:
            # Non-exempt — flag is_overtime, don't save hours until approved
            if not existing_approved_ot:
                attendance.overtime_hours = 0
                attendance.save(update_fields=['overtime_hours'])
            att_status.is_overtime = True
            att_status.save(update_fields=['is_overtime'])

            # Determine combined OT type for pre-fill in modal
            # Store pre/post hours on the attendance for the approval page to use
            attendance.overtime_hours = 0  # stays 0 until approved
            attendance.save(update_fields=['overtime_hours'])

    else:
        # No overtime detected — only clear if no approved OT request exists
        if not existing_approved_ot:
            att_status.is_overtime = False
            att_status.save(update_fields=['is_overtime'])

    # # ── Auto UT request ───────────────────────────────────────────────────
    # if undertime.is_undertime:
    #     ut_reason = _get_ut_reason(is_long_shift, is_24hr_shift, has_schedule, pairs, hours.actual_break)
    #     ut_obj, created = UndertimeRequest.objects.get_or_create(
    #         attendance=attendance,
    #         defaults={'filed_by': None, 'reason': ut_reason, 'status': 'PENDING'}
    #     )
    #     if not created and ut_obj.filed_by is None:
    #         ut_obj.reason = ut_reason
    #         ut_obj.save(update_fields=['reason'])
    # else:
    #     UndertimeRequest.objects.filter(
    #         attendance=attendance, status='PENDING', filed_by=None
    #     ).delete()

    # # ── Auto HD request ───────────────────────────────────────────────────
    # if halfday.is_halfday and not credited.disciplinary_action:
    #     HalfdayRequest.objects.get_or_create(
    #         employee=employee,
    #         date=work_date,
    #         defaults={
    #             'halfday_type': 'pm' if late.raw_late_hours >= HALFDAY_LATE_MIN else 'am',
    #             'filed_by':     None,
    #             'reason':       'Auto-detected halfday.',
    #             'status':       'PENDING',
    #         }
    #     )
    #     # suppress UT request when halfday exists
    #     UndertimeRequest.objects.filter(
    #         attendance=attendance, status='PENDING', filed_by=None
    #     ).delete()
    # else:
    #     HalfdayRequest.objects.filter(
    #         employee=employee, date=work_date, status='PENDING', filed_by=None
    #     ).delete()

    return attendance


def _check_night_diff(pairs, schedule):
    if not schedule or not schedule.crosses_midnight:
        return False
    for time_in, time_out in pairs:
        current = time_in
        while current <= time_out:
            t = timezone.localtime(current).time()
            if t >= _ND_START or t <= _ND_END:
                return True
            current += timedelta(minutes=30)
    return False