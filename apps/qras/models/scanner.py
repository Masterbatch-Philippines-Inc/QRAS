from django.db import models
from apps.qras.models.employee import Employee
from apps.qras.models.attendance import AttendanceLog
from datetime import datetime
from django.utils import timezone


def scan_image_path(instance, filename):
    today = datetime.now().strftime('%Y-%m-%d')
    return f"scans/{instance.employee.employee_id}/{today}/{filename}"


class ScanCapture(models.Model):
    employee    = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='scan_captures')
    attendance  = models.ForeignKey(AttendanceLog, on_delete=models.SET_NULL, null=True, related_name='capture')
    image       = models.ImageField(upload_to=scan_image_path)  # ← use the function
    action      = models.CharField(max_length=10)
    captured_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-captured_at']
        db_table = 'scan_captures'