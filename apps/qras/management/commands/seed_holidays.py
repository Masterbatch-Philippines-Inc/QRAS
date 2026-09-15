from datetime import date
from django.core.management.base import BaseCommand


# Fixed-date Philippine regular holidays (same date every year)
FIXED_REGULAR_HOLIDAYS = [
    ('New Year\'s Day',        1, 1),
    ('Araw ng Kagitingan',     4, 9),
    ('Labor Day',              5, 1),
    ('Independence Day',       6, 12),
    ('National Heroes Day',    8, 30),
    ('Bonifacio Day',          11, 30),
    ('Christmas Day',          12, 25),
    ('Rizal Day',              12, 30),
]

# Fixed-date special (non-working) holidays
FIXED_SPECIAL_HOLIDAYS = [
    ('Ninoy Aquino Day',       8, 21),
    ('All Saints\' Day',       11, 1),
    ('Feast of the Immaculate Conception', 12, 8),
    ('Last Day of the Year',  12, 31),
]


class Command(BaseCommand):
    help = (
        'Seeds fixed-date Philippine holidays for the current year. '
        'Movable holidays (e.g. Holy Week, Chinese New Year, Eid dates, '
        'proclaimed special dates) must be added manually since they change '
        'yearly and are announced via presidential proclamation. Safe to re-run.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Override the year to seed. Defaults to the current year.',
        )

    def handle(self, *args, **options):
        from apps.qras.models.attendance import Holiday

        year = options['year'] or date.today().year

        created_count = 0
        skipped_count = 0

        for name, month, day in FIXED_REGULAR_HOLIDAYS:
            obj, created = Holiday.objects.get_or_create(
                name=name,
                date=date(year, month, day),
                defaults={'is_recurring': True, 'type': 'regular'},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'[Holiday] Created: {name} ({obj.date})'))
            else:
                skipped_count += 1
                self.stdout.write(f'[Holiday] Already exists: {name} ({obj.date})')

        for name, month, day in FIXED_SPECIAL_HOLIDAYS:
            obj, created = Holiday.objects.get_or_create(
                name=name,
                date=date(year, month, day),
                defaults={'is_recurring': True, 'type': 'special_non_working'},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'[Holiday] Created: {name} ({obj.date})'))
            else:
                skipped_count += 1
                self.stdout.write(f'[Holiday] Already exists: {name} ({obj.date})')

        self.stdout.write(self.style.WARNING(
            'Note: movable holidays (Holy Thursday, Good Friday, Chinese New Year, '
            'Eid\'l Fitr, Eid\'l Adha, and any proclaimed additional special dates) '
            'were NOT seeded — these change yearly and must be added manually or '
            'via a separate proclamation-tracking process.'
        ))

        self.stdout.write(self.style.SUCCESS(
            f'Holiday seeding for {year} complete. {created_count} created, {skipped_count} already existed.'
        ))