from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Detect and sync missing attendance logs for a date or range of dates.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Single date to scan (YYYY-MM-DD). Defaults to yesterday.',
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Scan the last N days (e.g. --days 7). Overrides --date.',
        )