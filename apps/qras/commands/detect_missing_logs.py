# from datetime import date, timedelta
# from django.core.management.base import BaseCommand
# from apps.qras.modules.attendance.helpers import detect_and_sync_missing_logs


# class Command(BaseCommand):
#     help = 'Detect and sync missing attendance logs for a date or range of dates.'

#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--date',
#             type=str,
#             help='Single date to scan (YYYY-MM-DD). Defaults to yesterday.',
#         )
#         parser.add_argument(
#             '--days',
#             type=int,
#             help='Scan the last N days (e.g. --days 7). Overrides --date.',
#         )

#     def handle(self, *args, **options):
#             # [DISABLED] detect_and_sync_missing_logs() is now a no-op.
#             # Missing log detection is handled inline by _flag_past_missing_logs()
#             # in helpers.py, triggered on every record_attendance() call.
#             # This command is kept for future re-enablement without data loss.
#             self.stdout.write(self.style.WARNING(
#                 'detect_missing_logs is currently disabled. '
#                 'Missing log flags are set inline on AttendanceStatus.has_missing_log '
#                 'via _flag_past_missing_logs() on each clock event.'
#             ))