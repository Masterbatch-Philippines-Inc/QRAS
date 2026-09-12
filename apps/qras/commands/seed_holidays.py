# import holidays
# from django.core.management.base import BaseCommand
# from app.attendance.models import Holiday


# # ── Type mapping based on Proclamation No. 1006 ──────────────────────────────
# # Everything the library returns is either regular or special.
# # Eid dates from the library are estimated — flagged in the name.
# # Dates not in this map default to 'special' as a safe fallback.

# REGULAR_HOLIDAY_NAMES = {
#     "New Year's Day",
#     "Maundy Thursday",
#     "Good Friday",
#     "Araw ng Kagitingan",
#     "Labor Day",
#     "Independence Day",
#     "National Heroes Day",
#     "Bonifacio Day",
#     "Christmas Day",
#     "Rizal Day",
# }

# RECURRING_HOLIDAY_NAMES = {
#     "New Year's Day",
#     "Labor Day",
#     "Independence Day",
#     "Ninoy Aquino Day",
#     "Bonifacio Day",
#     "Christmas Day",
#     "Rizal Day",
#     "Feast of the Immaculate Conception of Mary",
#     "Last Day of the Year",
#     "Christmas Eve",
#     "All Saints' Day",
#     "All Souls' Day",
# }

# # Eid names from the library come with "(estimated)" appended.
# # These are regular holidays by law (RA 9177 and RA 9232),
# # even though exact dates are announced separately.
# EID_KEYWORDS = ("Eid'l Fitr", "Eid'l Adha", "Eid al-Fitr", "Eid al-Adha")


# def resolve_type(holiday_name):
#     """Returns 'regular' or 'special' based on the holiday name."""
#     if holiday_name in REGULAR_HOLIDAY_NAMES:
#         return 'regular'
#     if any(eid in holiday_name for eid in EID_KEYWORDS):
#         return 'regular'
#     return 'special'


# class Command(BaseCommand):
#     help = (
#         'Seeds the Holiday table with official Philippine holidays for 2026 '
#         'using the python-holidays library (Proclamation No. 1006). '
#         'Safe to run multiple times — duplicates are skipped.'
#     )
#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--year',
#             type=int,
#             default=2026,
#             help='The year to seed holidays for (default: 2026).',
#         )

#     def handle(self, *args, **kwargs):
#         year = kwargs['year']
#         ph_holidays = holidays.Philippines(years=year)

#         created_count = 0
#         skipped_count = 0

#         for holiday_date, holiday_name in sorted(ph_holidays.items()):
            
#             h_type = resolve_type(holiday_name)
            
#             is_recurring = holiday_name in RECURRING_HOLIDAY_NAMES
            
#             holiday_obj, created = Holiday.objects.get_or_create(
#                 date=holiday_date,
#                 defaults={
#                     'name':         holiday_name,
#                     'type':         h_type,
#                     'is_recurring': is_recurring,
#                 },
#             )

#             if created:
#                 created_count += 1
#                 self.stdout.write(
#                     self.style.SUCCESS(
#                         f"  Added   {holiday_obj.date}  "
#                         f"[{h_type.upper():8}]  {holiday_name}"
#                     )
#                 )
#             else:
#                 skipped_count += 1
#                 self.stdout.write(
#                     self.style.WARNING(
#                         f"  Skipped {holiday_date}  "
#                         f"[{h_type.upper():8}]  {holiday_name}  (already exists)"
#                     )
#                 )

#         self.stdout.write('')
#         self.stdout.write(
#             self.style.SUCCESS(f"Done for {year}. {created_count} added, {skipped_count} skipped.")
#         )
#         self.stdout.write(
#             self.style.WARNING(
#                 "Note: Eid dates are ESTIMATED by the library. "
#                 "Update them manually once the official proclamation is issued."
#             )
#         )