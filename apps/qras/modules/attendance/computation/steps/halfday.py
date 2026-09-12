# from ..dataclasses import HalfdayResult

# HALFDAY_HOUR_BUFFER = 0.5


# def compute_halfday(hours, late, halfday_threshold, is_present, has_schedule, has_time_out):

#     if not has_schedule or not has_time_out:
#         return HalfdayResult(
#             is_halfday=False,
#             is_halfday_by_hours=False,
#             is_halfday_by_late=False,
#         )

#     is_halfday_by_hours = is_present and (
#         (halfday_threshold - HALFDAY_HOUR_BUFFER)
#         <= hours.hours_within_shift <=
#         (halfday_threshold + HALFDAY_HOUR_BUFFER)
#     )

#     is_halfday = is_present and (is_halfday_by_hours or late.is_halfday_by_late)

#     return HalfdayResult(
#         is_halfday=is_halfday,
#         is_halfday_by_hours=is_halfday_by_hours,
#         is_halfday_by_late=late.is_halfday_by_late,
#     )