from django.core.management.base import BaseCommand
# from app.attendance.models import AttendanceLog, Attendance
# Import other models you want to sync here

class Command(BaseCommand):
    help = 'Syncs new records from the local default database to the server database.'
    def handle(self, *args, **options):
        from handlers.utils.sync_helpers import sync_all_models, sync_scan_files

        self.stdout.write("Starting database sync to server...")

        try:
            sync_all_models(self.stdout, self.style)
            sync_scan_files(self.stdout, self.style)
            self.stdout.write(self.style.SUCCESS('Sync completed.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Sync failed: {str(e)}'))