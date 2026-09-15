from django.utils.timezone import localdate


def get_today_count(dept=None):
    from apps.qras.models.attendance import AttendanceLog
    qs = AttendanceLog.objects.filter(date=localdate())
    if dept:
        qs = qs.filter(employee__department=dept)
    return qs.values('employee').distinct().count()


def get_ut_count(dept=None, user=None):
    from apps.qras.models.attendance import AttendanceStatus
    qs = AttendanceStatus.objects.filter(is_undertime=True)
    if dept:
        qs = qs.filter(attendance__employee__department=dept)
    if user:
        linked_emp = getattr(user, 'employee', None)
        if linked_emp:
            qs = qs.exclude(attendance__employee__pk=linked_emp.pk)
    return qs.count()


def get_ot_count(dept=None, user=None):
    from apps.qras.models.attendance import AttendanceStatus, OvertimeRequest
    from apps.qras.models.employee import Employee

    exempt_pks = list(
        Employee.objects
        .filter(group_memberships__group__ot_filing_exempted=True)
        .values_list('pk', flat=True)
        .distinct()
    )

    decided_att_ids = set(
        OvertimeRequest.objects
        .filter(status__in=['APPROVED', 'REJECTED'])
        .values_list('attendance_id', flat=True)
    )

    qs = AttendanceStatus.objects.filter(is_overtime=True)
    if dept:
        qs = qs.filter(attendance__employee__department=dept)

    qs = qs.exclude(attendance__employee__pk__in=exempt_pks)
    qs = qs.exclude(attendance__pk__in=decided_att_ids)

    if user:
        linked_emp = getattr(user, 'employee', None)
        if linked_emp:
            qs = qs.exclude(attendance__employee__pk=linked_emp.pk)

    return qs.count()


def get_hd_count(dept=None, user=None):
    from apps.qras.models.attendance import AttendanceStatus
    qs = AttendanceStatus.objects.filter(is_halfday=True)
    if dept:
        qs = qs.filter(attendance__employee__department=dept)
    if user:
        linked_emp = getattr(user, 'employee', None)
        if linked_emp:
            qs = qs.exclude(attendance__employee__pk=linked_emp.pk)
    return qs.count()


def get_ml_count(dept=None, user=None):
    from django.utils.timezone import localdate
    from apps.qras.models.attendance import AttendanceStatus
    qs = AttendanceStatus.objects.filter(
        has_missing_log=True,
        attendance__date__lt=localdate()
    )
    if dept:
        qs = qs.filter(attendance__employee__department=dept)
    if user:
        linked_emp = getattr(user, 'employee', None)
        if linked_emp:
            qs = qs.exclude(attendance__employee__pk=linked_emp.pk)
    return qs.count()


def get_ns_count(dept=None):
    from apps.qras.models.employee import Employee
    qs = Employee.objects.filter(
        is_active=True,
        is_resigned=False,
        attendance__isnull=False,
    )
    if dept:
        qs = qs.filter(department=dept)
    return qs.exclude(schedules__is_active=True).distinct().count()