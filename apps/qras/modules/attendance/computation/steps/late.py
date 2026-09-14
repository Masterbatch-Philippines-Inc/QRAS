from datetime import timedelta
from ...dataclasses import LateResult

HALFDAY_LATE_MIN = 1.0


def compute_late(first_time_in, start_aware, halfday_threshold, required_hours, has_schedule):

    if not has_schedule or first_time_in is None or first_time_in <= start_aware:
        return LateResult(
            is_late=False,
            late_hours=0.0,
            raw_late_hours=0.0,
            is_halfday_by_late=False,
        )

    raw_late_hours = (first_time_in - start_aware).total_seconds() / 3600
    is_late        = False
    late_hours     = 0.0

    if raw_late_hours >= HALFDAY_LATE_MIN:
        pm_session_start = start_aware + timedelta(
            hours=float(halfday_threshold) + 1.0  # BREAK_HOURS = 1.0
        )
        pm_late = (first_time_in - pm_session_start).total_seconds() / 3600
        if pm_late > 0:
            late_hours = round(pm_late, 2)
            is_late    = True
    elif raw_late_hours < required_hours:
        late_hours = round(raw_late_hours, 2)
        is_late    = True

    return LateResult(
        is_late=is_late,
        late_hours=late_hours,
        raw_late_hours=raw_late_hours,
        is_halfday_by_late=raw_late_hours >= HALFDAY_LATE_MIN,
    )