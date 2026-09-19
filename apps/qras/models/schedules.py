BREAK_HOURS = 1.0 

from django.db import models
from datetime import timedelta, datetime, date
from django.conf import settings


class ScheduleRecomputeEvent(models.Model):
    employee          = models.ForeignKey('qras.Employee', on_delete=models.CASCADE, related_name='recompute_events')
    old_schedule      = models.ForeignKey('ShiftSchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    new_schedule      = models.ForeignKey('ShiftSchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    recomputed_by     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    recomputed_at     = models.DateTimeField(auto_now_add=True)
    scope_description = models.CharField(max_length=100)  # e.g. "all", "single_date: 2026-03-01", "date_range: 2026-03-01 to 2026-03-15"

    def __str__(self):
        return f"Recompute | {self.employee} | {self.recomputed_at.date()}"

    class Meta:
        ordering = ['-recomputed_at']
        db_table = 'schedule_recompute_events'


class ScheduleRecomputeDetail(models.Model):
    event               = models.ForeignKey(ScheduleRecomputeEvent, on_delete=models.CASCADE, related_name='details')
    date                = models.DateField()
    before_time_in      = models.DateTimeField(null=True, blank=True)
    before_time_out     = models.DateTimeField(null=True, blank=True)
    before_credited_hrs = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    after_time_in       = models.DateTimeField(null=True, blank=True)
    after_time_out      = models.DateTimeField(null=True, blank=True)
    after_credited_hrs  = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    def __str__(self):
        return f"Detail | {self.event.employee} | {self.date}"

    class Meta:
        ordering = ['date']
        db_table = 'schedule_recompute_details'


class ShiftSchedule(models.Model):
    """
    Replaces WorkPolicy. One row per named schedule (Day Sched, Night Sched, etc.).
    required_hours is derived from shift_end - shift_start - 1h break (not stored).
    """
    name                = models.CharField(max_length=100)
    shift_start         = models.TimeField()
    shift_end           = models.TimeField()
    halfday_threshold   = models.DecimalField(max_digits=4, decimal_places=2, default=4)
    crosses_midnight    = models.BooleanField(default=False)
    is_active           = models.BooleanField(default=True)
    is_global           = models.BooleanField(default=False)
    rest_days           = models.JSONField(default=list, blank=True)
    specific_dates      = models.JSONField(default=list, blank=True)
    created_by          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_schedules')
    
    @property
    def specific_dates_json(self):
        import json
        return json.dumps(self.specific_dates or [])
 
    @property
    def required_hours(self):
        """Returns required work hours as a float (shift duration minus fixed 1h break)."""
        base = date.today()
        s = datetime.combine(base, self.shift_start)
        e = datetime.combine(
            base + timedelta(days=1) if self.crosses_midnight else base,
            self.shift_end
        )
        return round((e - s).total_seconds() / 3600 - BREAK_HOURS, 2)
 
    def __str__(self):
        return self.name
 
    class Meta:
        ordering = ['name']
        db_table = 'schedule_shifts'


class ScheduleActivityLog(models.Model):
    employee          = models.ForeignKey('qras.Employee', on_delete=models.CASCADE, related_name='schedule_activity_logs')
    assigned_schedule = models.ForeignKey('ShiftSchedule', on_delete=models.SET_NULL, null=True, related_name='+')
    previous_schedule = models.ForeignKey('ShiftSchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    acted_by          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    acted_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-acted_at']
        db_table = 'schedule_activity_logs'


# ─────────────────────────────────────────────────────────────────────────────
#  DATE-SPECIFIC OVERRIDE — highest priority in schedule resolution
# ─────────────────────────────────────────────────────────────────────────────

class EmployeeScheduleOverride(models.Model):
    """
    Temporary, date-ranged patch on top of an employee's normal schedule
    (whether that's a single default ShiftSchedule or a rotation assignment).
    Does not touch the employee's underlying schedule/rotation setup and
    stops applying automatically once date_to has passed.
    """
    employee   = models.ForeignKey('qras.Employee', on_delete=models.CASCADE, related_name='schedule_overrides')
    schedule   = models.ForeignKey('ShiftSchedule', on_delete=models.CASCADE, related_name='+')
    date_from  = models.DateField()
    date_to    = models.DateField()
    reason     = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Override | {self.employee} | {self.date_from} to {self.date_to} → {self.schedule}"

    class Meta:
        ordering = ['-date_from']
        db_table = 'employee_schedule_overrides'


# ─────────────────────────────────────────────────────────────────────────────
#  ROTATION SYSTEM — day-level, week-cycled, team-based shift assignment
# ─────────────────────────────────────────────────────────────────────────────

class RotationGroup(models.Model):
    """
    One rotating shift setup, e.g. 'Ops 3-Shift Rotation'.
    anchor_date is any date that falls within week_index 0 of the cycle
    (recommended: a Monday) — used to compute which week of the cycle a
    given work_date falls into.
    """
    name         = models.CharField(max_length=100)
    cycle_weeks  = models.PositiveIntegerField(default=1)
    anchor_date  = models.DateField()
    is_active    = models.BooleanField(default=True)
    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def week_index_for(self, work_date):
        delta_days = (work_date - self.anchor_date).days
        return (delta_days // 7) % self.cycle_weeks

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        db_table = 'rotation_groups'


class RotationSlot(models.Model):
    """A named shift slot within a rotation group, e.g. '1st' = 18:00-06:00."""
    group    = models.ForeignKey(RotationGroup, on_delete=models.CASCADE, related_name='slots')
    name     = models.CharField(max_length=50)   # e.g. "1st", "2nd", "3rd"
    schedule = models.ForeignKey('ShiftSchedule', on_delete=models.CASCADE, related_name='+')
    order    = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.group.name} — {self.name}"

    class Meta:
        ordering = ['group', 'order']
        db_table = 'rotation_slots'


class RotationTeam(models.Model):
    """A named crew within a rotation group, e.g. 'Lead A & Team'."""
    group = models.ForeignKey(RotationGroup, on_delete=models.CASCADE, related_name='teams')
    name  = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.group.name} — {self.name}"

    class Meta:
        ordering = ['group', 'name']
        db_table = 'rotation_teams'


class RotationTeamMembership(models.Model):
    employee = models.ForeignKey('qras.Employee', on_delete=models.CASCADE, related_name='rotation_memberships')
    team     = models.ForeignKey(RotationTeam, on_delete=models.CASCADE, related_name='members')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee} — {self.team}"

    class Meta:
        unique_together = ('employee', 'team')
        db_table = 'rotation_team_memberships'


class RotationAssignment(models.Model):
    """
    For a given rotation group, which team works which slot on a given
    week_index (0-based, wraps at cycle_weeks) of the cycle.
    """
    group      = models.ForeignKey(RotationGroup, on_delete=models.CASCADE, related_name='assignments')
    week_index = models.PositiveIntegerField()
    slot       = models.ForeignKey(RotationSlot, on_delete=models.CASCADE, related_name='assignments')
    team       = models.ForeignKey(RotationTeam, on_delete=models.CASCADE, related_name='assignments')

    def __str__(self):
        return f"{self.group.name} | wk{self.week_index} | {self.slot.name} → {self.team.name}"

    class Meta:
        unique_together = ('group', 'week_index', 'slot')
        db_table = 'rotation_assignments'