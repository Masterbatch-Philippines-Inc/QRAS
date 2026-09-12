from ..dataclasses import UndertimeResult
from app.schedules.models import BREAK_HOURS
from datetime import timedelta


def compute_undertime(pairs, hours, completion, halfday, has_schedule, is_long_shift, is_24hr_shift, start_aware, end_aware, required_hours, is_present, halfday_threshold=4.0):

    if not has_schedule or not pairs:
        return UndertimeResult(undertime=0.0, is_undertime=False)

    if is_long_shift and not is_24hr_shift:
        undertime = max(required_hours - hours.total_hours_raw, 0.0)

    elif halfday.is_halfday and not halfday.is_halfday_by_late:
        # PRE-HD completed — no undertime
        undertime = 0.0

    elif not halfday.is_halfday and hours.hours_within_shift < halfday_threshold:
        # PRE-UT — left before halfday threshold (before break time)
        # Undertime excludes the break window: (last_out → break_start) + (break_end → shift_end)
        break_win_start = start_aware + timedelta(hours=halfday_threshold)
        break_win_end   = break_win_start + timedelta(hours=BREAK_HOURS)
        last_out        = pairs[-1][1]
        pre_break       = max((break_win_start - last_out).total_seconds() / 3600, 0.0)
        post_break      = max((end_aware - break_win_end).total_seconds() / 3600, 0.0)
        undertime       = pre_break + post_break

    else:
        if completion.timed_out_on_time:
            undertime = 0.0
        else:
            last_out  = pairs[-1][1]
            undertime = max((end_aware - last_out).total_seconds() / 3600, 0.0)

    # halfday by late — zero out undertime
    if halfday.is_halfday and halfday.is_halfday_by_late:
        undertime = 0.0

    is_undertime = (
        has_schedule
        and is_present
        and not completion.is_completed
        and undertime > 0
        and not (halfday.is_halfday and not halfday.is_halfday_by_late)
    )

    return UndertimeResult(
        undertime=round(undertime, 2),
        is_undertime=is_undertime,
    )