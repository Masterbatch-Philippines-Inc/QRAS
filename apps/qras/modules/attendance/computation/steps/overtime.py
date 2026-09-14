from datetime import timedelta
from django.utils import timezone
from decouple import config as _config
from apps.qras.models.management import BREAK_HOURS
from ...dataclasses import OvertimeResult

PRE_OT_THRESHOLD  = float(_config('PRE_OT_THRESHOLD_HOURS',  default=1.0))
POST_OT_THRESHOLD = float(_config('POST_OT_THRESHOLD_HOURS', default=1.0))


def _split_24hr_schedule(schedule, work_date):
    tz = timezone.get_current_timezone()
    shift_start = timezone.make_aware(
        __import__('datetime').datetime.combine(work_date, schedule.shift_start), tz
    )
    sub1_start = shift_start
    sub1_end   = shift_start + timedelta(hours=9)
    sub2_start = shift_start + timedelta(hours=12)
    sub2_end   = shift_start + timedelta(hours=21)
    return (sub1_start, sub1_end), (sub2_start, sub2_end)


def compute_overtime(pairs, hours, has_schedule, is_long_shift, is_24hr_shift, start_aware, end_aware, required_hours, schedule, work_date):

    if not has_schedule or not pairs:
        return OvertimeResult(overtime=0.0, pre_overtime=0.0)

    if is_24hr_shift:
        (sub1_s, sub1_e), (sub2_s, sub2_e) = _split_24hr_schedule(schedule, work_date)

        def hours_in_window(start, end):
            total = 0.0
            for inn, out in pairs:
                ws = max(inn, start)
                we = min(out, end)
                d  = (we - ws).total_seconds() / 3600
                if d > 0:
                    total += d
            return total

        ot1 = hours_in_window(sub1_e, sub2_s)
        ot2 = hours_in_window(sub2_e, sub2_e + timedelta(hours=3))
        return OvertimeResult(overtime=ot1 + ot2, pre_overtime=0.0)

    if is_long_shift and not is_24hr_shift:
        if has_schedule and schedule.crosses_midnight and pairs and start_aware:
            required_end = start_aware + timedelta(hours=required_hours + BREAK_HOURS)
            last_out     = min(pairs[-1][1], end_aware)
            overtime     = max((last_out - required_end).total_seconds() / 3600, 0.0)
            return OvertimeResult(overtime=round(overtime, 2), pre_overtime=0.0)
        else:
            return OvertimeResult(
                overtime=max(hours.total_hours_raw - required_hours, 0.0),
                pre_overtime=0.0,
            )

    # Post-shift OT — only if past shift end by more than threshold
    post_ot = 0.0
    last_out = pairs[-1][1]
    if last_out > end_aware:
        late_hours = (last_out - end_aware).total_seconds() / 3600
        if late_hours > POST_OT_THRESHOLD:
            post_ot = late_hours

    # Pre-shift OT — only if early by more than threshold
    pre_ot = 0.0
    first_in = pairs[0][0]
    if first_in < start_aware:
        early_hours = (start_aware - first_in).total_seconds() / 3600
        if early_hours > PRE_OT_THRESHOLD:
            pre_ot = early_hours

    return OvertimeResult(
        overtime=round(post_ot, 2),
        pre_overtime=round(pre_ot, 2),
    )

