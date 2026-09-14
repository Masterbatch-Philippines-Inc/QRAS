from django.utils import timezone
from datetime import timedelta
from apps.qras.models.management import BREAK_HOURS
from ...dataclasses import HoursResult


def compute_hours(pairs, has_schedule, is_long_shift, is_24hr_shift, start_aware, end_aware, halfday_threshold, schedule, work_date):

    actual_hours_worked = 0.0
    hours_within_shift  = 0.0
    total_hours_raw     = 0.0
    total_work_display  = 0.0

    # ── Actual hours worked — uncapped ────────────────────────────────────
    for inn, out in pairs:
        duration = (out - inn).total_seconds() / 3600
        if duration > 0:
            actual_hours_worked += duration

    # ── Hours within shift — capped to shift boundaries ───────────────────
    for inn, out in pairs:
        if has_schedule:
            work_start = max(inn, start_aware)
            work_end   = min(out, end_aware)
        else:
            work_start = inn
            work_end   = out
        duration = (work_end - work_start).total_seconds() / 3600
        if duration > 0:
            hours_within_shift += duration

    # ── Actual break ──────────────────────────────────────────────────────
    if has_schedule and len(pairs) > 1:
        shift_pairs = [(inn, out) for inn, out in pairs if out > start_aware and inn < end_aware]
        actual_break = (
            (shift_pairs[1][0] - shift_pairs[0][1]).total_seconds() / 3600
            if len(shift_pairs) > 1 else 0.0
        )
    elif len(pairs) > 1:
        actual_break = (
            (pairs[1][0] - pairs[0][1]).total_seconds() / 3600
        )
    else:
        actual_break = 0.0

    # ── Strip break window overlap ────────────────────────────────────────
    if has_schedule and len(pairs) > 1 and actual_break > BREAK_HOURS:
        break_win_start = start_aware + timedelta(hours=float(halfday_threshold))
        break_win_end   = break_win_start + timedelta(hours=BREAK_HOURS)
        for inn, out in pairs:
            if break_win_start <= inn < break_win_end:
                old = max(0.0, (min(out, end_aware) - max(inn, start_aware)).total_seconds() / 3600)
                new = max(0.0, (min(out, end_aware) - break_win_end).total_seconds() / 3600)
                hours_within_shift  -= (old - new)
                actual_hours_worked -= (old - new)

    # ── 24hr shift special case ───────────────────────────────────────────
    if is_24hr_shift and pairs:
        from ..steps.overtime import _split_24hr_schedule
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

        sub1_raw = max(0.0, hours_in_window(sub1_s, sub1_e) - BREAK_HOURS)
        sub2_raw = max(0.0, hours_in_window(sub2_s, sub2_e) - BREAK_HOURS)

        total_hours_raw    = sub1_raw + sub2_raw
        hours_within_shift = total_hours_raw

        actual_break_total = (
            (pairs[1][0] - pairs[0][1]).total_seconds() / 3600
            if len(pairs) > 1 else 0.0
        )
        total_work_display = max(0.0, actual_hours_worked - max(0.0, (BREAK_HOURS * 2) - actual_break_total))

    # ── Unscheduled — raw hours, no break deduction ───────────────────────
    elif not has_schedule:
        total_hours_raw    = actual_hours_worked
        total_work_display = actual_hours_worked

    # ── Normal scheduled ──────────────────────────────────────────────────
    else:
        if not pairs:
            total_hours_raw    = 0.0
            total_work_display = 0.0
        elif is_long_shift:
            if len(pairs) > 1:
                total_hours_raw    = max(0.0, hours_within_shift - max(0.0, BREAK_HOURS - actual_break))
                total_work_display = max(0.0, actual_hours_worked - max(0.0, BREAK_HOURS - actual_break))
            else:
                total_hours_raw    = max(0.0, hours_within_shift - BREAK_HOURS)
                total_work_display = max(0.0, actual_hours_worked - BREAK_HOURS)
        elif len(pairs) > 1:
            total_hours_raw    = max(0.0, hours_within_shift - max(0.0, BREAK_HOURS - actual_break))
            total_work_display = max(0.0, actual_hours_worked - max(0.0, BREAK_HOURS - actual_break))
        else:
            if hours_within_shift < halfday_threshold:
                # Employee left before break window — no break to deduct
                total_hours_raw    = hours_within_shift
                total_work_display = actual_hours_worked
            else:
                total_hours_raw    = max(0.0, hours_within_shift - BREAK_HOURS)
                total_work_display = max(0.0, actual_hours_worked - BREAK_HOURS)

    return HoursResult(
        actual_hours_worked=actual_hours_worked,
        hours_within_shift=hours_within_shift,
        total_hours_raw=total_hours_raw,
        total_work_display=total_work_display,
        actual_break=actual_break,
    )