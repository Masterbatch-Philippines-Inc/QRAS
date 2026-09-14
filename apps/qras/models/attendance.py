from django.db import models
from django.conf import settings


class Attendance(models.Model):
	employee         = models.ForeignKey('qras.Employee', on_delete=models.CASCADE)
	date             = models.DateField()
	schedule         = models.ForeignKey('qras.ShiftSchedule', null=True, blank=True, on_delete=models.SET_NULL)
	total_work_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
	overtime_hours   = models.DecimalField(max_digits=6, decimal_places=2, default=0)
	undertime_hours  = models.DecimalField(max_digits=6, decimal_places=2, default=0)
	late_hours       = models.DecimalField(max_digits=5, decimal_places=2, default=0)
	created_at       = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		unique_together = ('employee', 'date')
		db_table = 'attendance'


class AttendanceStatus(models.Model):
	STATUS_CHOICES = [
		('PENDING',  'Pending'),
		('APPROVED', 'Approved'),
		('REJECTED', 'Rejected'),
		('RECORDED', 'Recorded'),
	]
	attendance     = models.OneToOneField(Attendance, on_delete=models.CASCADE, related_name='att_status')
	credited_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
	is_present     = models.BooleanField(default=False)
	is_late        = models.BooleanField(default=False)
	is_halfday     = models.BooleanField(default=False)
	is_completed   = models.BooleanField(default=False)
	is_overtime    = models.BooleanField(default=False)
	is_undertime   = models.BooleanField(default=False)
	has_night_diff = models.BooleanField(default=False)
	is_sunday      = models.BooleanField(default=False)
	is_regular_holiday = models.BooleanField(default=False)
	is_special_holiday = models.BooleanField(default=False)
	is_absent      = models.BooleanField(default=False)
	has_missing_log = models.BooleanField(default=False)
	status         = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')
	
	class Meta:
		db_table = 'attendance_status'


class AttendanceLog(models.Model):
    employee        = models.ForeignKey('qras.Employee', on_delete=models.CASCADE)
    date            = models.DateField()
    timestamp       = models.DateTimeField()
    is_time_in      = models.BooleanField(default=False)
    is_time_out     = models.BooleanField(default=False)
    att_source      = models.CharField(
        max_length  = 20,
        choices     = [('qr', 'QR Scan'), ('manual', 'Manual Entry')],
        default     = 'qr'
    )
    is_replaced     = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date')
        db_table = 'attendance_logs'


class AttendanceLogAudit(models.Model):
    original_log  = models.ForeignKey(AttendanceLog, on_delete=models.SET_NULL, null=True, related_name='audits')
    employee      = models.ForeignKey('Employee', on_delete=models.CASCADE)
    original_time = models.DateTimeField()
    replaced_at   = models.DateTimeField(auto_now_add=True)
    replaced_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    log_type      = models.CharField(max_length=10)  # 'time_in' or 'time_out'
    reason        = models.TextField(blank=True)

    class Meta:
        db_table = 'attendance_log_audits'


class Holiday(models.Model):
    name         = models.CharField(max_length=100)
    date         = models.DateField()
    is_recurring = models.BooleanField(default=False)
    type         = models.CharField(max_length=30, default='regular')

    class Meta:
        db_table = 'holidays'


class OvertimeRequest(models.Model):
    OT_TYPE_CHOICES = [
        ('pre_shift',  'Pre-Shift'),
        ('post_shift', 'Post-Shift'),
    ]
    STATUS_CHOICES = [
        ('PENDING',  'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    attendance = models.OneToOneField(
        'Attendance',
        on_delete=models.CASCADE,
        related_name='ot_request'
    )
    filed_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    ot_type    = models.CharField(max_length=10, choices=OT_TYPE_CHOICES)
    ot_start   = models.TimeField()
    ot_end     = models.TimeField()
    ot_hours   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    filed_at   = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    remarks    = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"OT {self.ot_type} | {self.attendance.employee} | {self.attendance.date}"

    class Meta:
        ordering = ['-filed_at']
        db_table = 'overtime_requests'


class UndertimeRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    APPROVAL_SOURCE_CHOICES = [
        ('manual', 'Manually Approved'),
        ('leave',  'Approved via Leave Request'),
    ]
    attendance      = models.OneToOneField('Attendance', on_delete=models.CASCADE, related_name='ut_request')
    filed_by        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason          = models.TextField()
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    filed_at        = models.DateTimeField(auto_now_add=True)
    decided_at      = models.DateTimeField(null=True, blank=True)
    remarks         = models.TextField(null=True, blank=True)
    approval_source = models.CharField(max_length=10, choices=APPROVAL_SOURCE_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"UT | {self.attendance.employee} | {self.attendance.date}"

    class Meta:
        ordering = ['-filed_at']
        db_table = 'undertime_requests'


class HalfdayRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    HALFDAY_TYPE_CHOICES = [
        ('am', 'AM'),
        ('pm', 'PM'),
    ]
    employee     = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='halfday_requests')
    date         = models.DateField()
    halfday_type = models.CharField(max_length=2, choices=HALFDAY_TYPE_CHOICES)
    filed_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason       = models.TextField(null=True, blank=True)
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    filed_at     = models.DateTimeField(auto_now_add=True)
    decided_at   = models.DateTimeField(null=True, blank=True)
    remarks      = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"HD | {self.employee} | {self.date}"

    class Meta:
        ordering = ['-filed_at']
        unique_together = ('employee', 'date')
        db_table = 'halfday_requests'


class LeaveRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('sick',      'Sick Leave'),
        ('vacation',  'Vacation Leave'),
        ('undertime', 'Undertime Leave'),
    ]
    STATUS_CHOICES = [
        ('PENDING',  'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    employee            = models.ForeignKey('qras.Employee', on_delete=models.CASCADE, related_name='leave_requests')
    lf_number           = models.CharField(max_length=50, blank=True)
    form_code           = models.CharField(max_length=50, blank=True)
    leave_type          = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    reason              = models.TextField()
    date_from           = models.DateField()
    date_to             = models.DateField()
    num_days            = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    signature_of_employee = models.CharField(max_length=100, blank=True)
    conformed_by        = models.CharField(max_length=100, blank=True)
    noted_by            = models.CharField(max_length=100, blank=True)
    status              = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    filed_by            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    filed_at            = models.DateTimeField(auto_now_add=True)
    decided_at          = models.DateTimeField(null=True, blank=True)
    remarks             = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-filed_at']
        db_table = 'leave_requests'

    def __str__(self):
        return f"{self.leave_type} | {self.employee} | {self.date_from} to {self.date_to}"


class Absents(models.Model):
    employee      = models.ForeignKey('qras.Employee', on_delete=models.CASCADE, related_name='excusals')
    date          = models.DateField()
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='excusals')
    excused_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    excused_at    = models.DateTimeField(auto_now_add=True)
    note          = models.TextField(blank=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-excused_at']
        db_table = 'absents'

    def __str__(self):
        return f"Excused | {self.employee} | {self.date}"


class MissingLog(models.Model):
    LOG_TYPE_CHOICES = [
        ('time_in',  'Time In'),
        ('time_out', 'Time Out'),
    ]
    STATUS_CHOICES = [
        ('PENDING',   'Pending'),
        ('RESOLVED',  'Resolved'),
        ('DISMISSED', 'Dismissed'),
    ]
    employee    = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='missing_logs')
    date        = models.DateField()
    log_type    = models.CharField(max_length=10, choices=LOG_TYPE_CHOICES)  # the MISSING one
    time_in     = models.TimeField(null=True, blank=True)   # recorded time in, if it exists
    time_out    = models.TimeField(null=True, blank=True)   # recorded time out, if it exists
    status      = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    filed_at    = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_missing_logs'
    )

    class Meta:
        unique_together = ('employee', 'date', 'log_type')
        ordering = ['-filed_at']
        db_table = 'missing_logs'

    def __str__(self):
        return f"Missing {self.log_type} | {self.employee} | {self.date}"