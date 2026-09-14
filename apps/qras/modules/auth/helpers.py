def get_dept_queryset_filter(request, dept_field_path='employee__department'):
    """
    Returns a dict to pass into .filter() for department-scoped views.

    - Admin: no filter (sees everything)
    - Dept Head with department: filters by their assigned department
    - Dept Head without department: returns None (caller should show alert)

    Usage:
        dept_filter = get_dept_queryset_filter(request)
        if dept_filter is None:
            return render(request, template, {'dept_warning': True})
        qs = SomeModel.objects.filter(**dept_filter)
    """
    role = getattr(request.user, 'role', None)

    if not role or role.name == 'Admin':
        return {}

    if role.name == 'Department Head':
        dept = getattr(request.user, 'department', None)
        if not dept:
            return None  # caller handles the no-dept case
        return {dept_field_path: dept}

    return {}


def get_self_exclude(request):
    """
    Returns the Employee pk to exclude from querysets so the
    dept head doesn't see their own employee record.
    Returns None if user has no linked employee.
    """
    emp = getattr(request.user, 'employee', None)
    return emp.pk if emp else None


def has_no_department(request):
    """
    Convenience check — True if user is a Dept Head with no department assigned.
    Use this in templates to show the alert.
    """
    role = getattr(request.user, 'role', None)
    if role and role.name == 'Department Head':
        return not getattr(request.user, 'department', None)
    return False