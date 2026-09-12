# from datetime import timedelta
# from ..dataclasses import CompletionResult


# def compute_completion(pairs, hours, late, has_schedule, is_long_shift, is_24hr_shift, end_aware, required_hours):

#     if not pairs:
#         return CompletionResult(is_completed=False, timed_out_on_time=False)

#     if not has_schedule:
#         return CompletionResult(
#             is_completed=hours.total_hours_raw >= required_hours,
#             timed_out_on_time=False,
#         )

#     if is_long_shift and not is_24hr_shift:
#         return CompletionResult(
#             is_completed=hours.total_hours_raw >= required_hours,
#             timed_out_on_time=False,
#         )

#     timed_out_on_time = pairs[-1][1] >= (end_aware - timedelta(seconds=60))

#     if late.is_halfday_by_late:
#         is_completed = timed_out_on_time
#     else:
#         is_completed = timed_out_on_time and hours.total_hours_raw >= required_hours

#     return CompletionResult(
#         is_completed=is_completed,
#         timed_out_on_time=timed_out_on_time,
#     )