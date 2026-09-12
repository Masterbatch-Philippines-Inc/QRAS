from ..dataclasses import CreditedResult


def compute_credited(hours, late, halfday, undertime, completion, halfday_threshold, required_hours, is_24hr_shift, sub1_raw=0.0, sub2_raw=0.0):

    disciplinary_action = halfday.is_halfday_by_late and not completion.is_completed

    if halfday.is_halfday:
        if disciplinary_action:
            credited = 0.0
        else:
            total_hours = (
                min(hours.hours_within_shift, halfday_threshold)
                if halfday.is_halfday_by_late
                else hours.hours_within_shift
            )
            if halfday.is_halfday_by_late:
                # late >= 60mins — no late deduction, PM session only counted
                credited = min(total_hours, halfday_threshold)
            else:
                # late < 60mins — deduct late
                credited = max(total_hours - late.late_hours, 0.0)

    elif is_24hr_shift:
        credited = min(sub1_raw, 8.0) + min(sub2_raw, 8.0)

    elif undertime.is_undertime:
        credited = 0.0

    else:
        total_hours = hours.total_hours_raw
        credited    = min(total_hours, required_hours)

    return CreditedResult(
        credited=round(credited, 2),
        disciplinary_action=disciplinary_action,
    )