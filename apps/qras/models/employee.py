from django.db import models
from django.conf import settings
from apps.qras.models.management import ShiftSchedule
from datetime import date
from qras.models.access import Department, Position


class Employee(models.Model):
    employee_id      = models.IntegerField(unique=True)
    first_name       = models.CharField(max_length=100)
    middle_name      = models.CharField(max_length=100, blank=True)
    last_name        = models.CharField(max_length=100)
    suffix_name      = models.CharField(max_length=100, blank=True)
    department       = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    position         = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True)
    hire_date        = models.DateField(null=True, blank=True)
    date_regularized = models.DateField(null=True, blank=True)
    date_resigned    = models.DateField(null=True, blank=True)
    is_active        = models.BooleanField(default=True)
    is_resigned      = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'employees'


class EmployeeRestDay(models.Model):
    employee   = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='rest_days')
    date       = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['date']
        db_table = 'employee_rest_days'

    def __str__(self):
        return f"{self.employee} — {self.date}"


class EmployeeContact(models.Model):
    employee           = models.OneToOneField('Employee', on_delete=models.CASCADE, related_name='contact')
    contact_no         = models.CharField(max_length=15, blank=True)
    address_1          = models.TextField(blank=True)
    address_2          = models.TextField(blank=True)
    sos_contact_person = models.CharField(max_length=100, blank=True)
    sos_contact_no     = models.CharField(max_length=15, blank=True)

    class Meta:
        db_table = 'employee_contact'


class EmployeeGovernmentID(models.Model):
    employee      = models.OneToOneField('Employee', on_delete=models.CASCADE, related_name='gov_ids')
    tin_no        = models.CharField(max_length=15, blank=True)
    sss_no        = models.CharField(max_length=15, blank=True)
    philhealth_no = models.CharField(max_length=15, blank=True)
    pagibig_no    = models.CharField(max_length=15, blank=True)

    class Meta:
        db_table = 'employee_government_ids'


class EmployeeSchedule(models.Model):
    employee       = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='schedules')
    schedule       = models.ForeignKey(ShiftSchedule, on_delete=models.SET_NULL, null=True)
    effective_date = models.DateField()
    is_active      = models.BooleanField(default=True)

    class Meta:
        unique_together = ('employee', 'schedule', 'effective_date')
        db_table = 'employee_schedules'


class EmployeeDetails(models.Model):
    employee   = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='details')
    birth_date = models.DateField(null=True, blank=True)

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    class Meta:
        db_table = 'employee_details'


class EmployeeGroup(models.Model):
    group_name        = models.CharField(max_length=50)
    ot_filing_exempted = models.BooleanField(default=False)
    is_active          = models.BooleanField(default=True)

    def __str__(self):
        return self.group_name

    class Meta:
        ordering = ['group_name']
        db_table = 'employee_groups'


class EmployeeGroupMembership(models.Model):
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )
    group = models.ForeignKey(
        EmployeeGroup,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    def __str__(self):
        return f"{self.employee} — {self.group}"

    class Meta:
        unique_together = ('employee', 'group')
        db_table = 'employee_group_memberships'