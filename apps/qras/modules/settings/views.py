from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings

from apps.qras.models.auth import User
from apps.qras.models.access import Role, Module, RolePermission, Role as SystemRole, Department

from django.utils.decorators import method_decorator
from apps.qras.modules.auth.decorators import permission_required

from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse_lazy

from django.db import models as django_models
from apps.qras.models.employee import Employee as EmployeeModel
from apps.qras.models.attendance import OvertimeRequest, UndertimeRequest, HalfdayRequest, LeaveRequest, MissingLog

from apps.qras.modules.auth.views import _generate_password, _generate_username



# ─────────────────────────────────────────────────────────────────
#   SYSTEM USERS — CBV
# ─────────────────────────────────────────────────────────────────

@method_decorator([permission_required('settings_system_users', 'read')], name='dispatch')
class SystemUserListView(LoginRequiredMixin, ListView):
    '''
    Notable behaviors:
    - The current logged-in user has no Edit/Deactivate buttons on their own row — shows "Current user" instead, so no self-lockout
    - Email send failure doesn't block user creation — it returns a warning alert instead so you know to share credentials manually
    - The deactivated users modal's Reactivate button is disabled when the list is empty
    - Select All checkbox in the deactivated modal is also disabled when empty
    '''
    
    model               = User
    template_name       = 'pages/settings/system_users.django'
    context_object_name = 'system_users'

    def get_queryset(self):
        show_inactive = self.request.GET.get('show_inactive') == 'true'
        search        = self.request.GET.get('q', '').strip()
        qs = User.objects.all() if show_inactive else User.objects.filter(is_active=True)
        if search:
            qs = qs.filter(
                django_models.Q(first_name__icontains=search) |
                django_models.Q(last_name__icontains=search)  |
                django_models.Q(email__icontains=search)
            )
        return qs.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['role_choices']        = SystemRole.objects.filter(is_active=True).order_by('name')
        ctx['department_choices']  = Department.objects.filter(is_active=True).order_by('name')
        ctx['employee_choices']    = EmployeeModel.objects.filter(
            is_active=True, is_resigned=False
        ).order_by('last_name', 'first_name')
        ctx['show_inactive'] = self.request.GET.get('show_inactive') == 'true'
        ctx['search']        = self.request.GET.get('q', '').strip()
        logged_in_ids = set(
            User.objects.filter(is_online=True).values_list('pk', flat=True)
        )
        ctx['logged_in_ids'] = logged_in_ids
        return ctx

@method_decorator([permission_required('settings_system_users', 'create')], name='dispatch')
class SystemUserCreateView(LoginRequiredMixin, View):

    def post(self, request):
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        role_id    = request.POST.get('role', '').strip()
        email      = request.POST.get('email', '').strip()

        # ── Validation ──────────────────────────────────────────
        if not all([first_name, last_name, email, role_id]):
            return JsonResponse({
                'status': 'error',
                'message': 'Last name, first name, email, and role are required.'
            })

        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'That email address is already in use.'
            })

        # ── Get Role Object ─────────────────────────────────────
        role_obj = SystemRole.objects.filter(
            pk=role_id,
            is_active=True
        ).first()

        if not role_obj:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid role selected.'
            })

        # ── Department Object ───────────────────────────────────
        department_obj = None
        if role_obj.name == 'Department Head':
            dept_id = request.POST.get('department', '').strip()
            if not dept_id:
                return JsonResponse({'status': 'error', 'message': 'Department is required for Department Head role.'})
            department_obj = Department.objects.filter(pk=dept_id, is_active=True).first()
            if not department_obj:
                return JsonResponse({'status': 'error', 'message': 'Invalid department selected.'})

        # ── Create user ─────────────────────────────────────────
        password = _generate_password()
        username = _generate_username(first_name, last_name)
        employee_id  = request.POST.get('employee', '').strip()
        employee_obj = EmployeeModel.objects.filter(pk=employee_id).first() if employee_id else None

        User.objects.create_user(
            username   = username,
            email      = email,
            password   = password,
            first_name = first_name,
            last_name  = last_name,
            role       = role_obj,
            department = department_obj,
            employee   = employee_obj,
        )

        # ── Send credentials via email ──────────────────────────
        email_sent = True

        try:
            send_mail(
                subject='Your MBPI-QRAS account',
                message=(
                    f"Hello {first_name},\n\n"
                    f"An account has been created for you on the MBPI QR Attendance System.\n\n"
                    f"Username : {username}\n"
                    f"Password : {password}\n\n"
                    f"Please log in and change your password as soon as possible.\n\n"
                    f"— MBPI-QRAS IT Admin"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            email_sent = False

        return JsonResponse({
            'status': 'created',
            'email_sent': email_sent
        })

@method_decorator([permission_required('settings_system_users', 'update')], name='dispatch')
class SystemUserUpdateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found.'})

        role  = request.POST.get('role',  '').strip()
        email = request.POST.get('email', '').strip()

        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email is required.'})

        if User.objects.filter(email=email).exclude(pk=pk).exists():
            return JsonResponse({'status': 'error', 'message': 'That email address is already in use.'})

        # ── Dept Head department handling ────────────────────────
        role_obj = SystemRole.objects.filter(pk=role, is_active=True).first()
        department_obj = None
        if role_obj and role_obj.name == 'Department Head':
            dept_id = request.POST.get('department', '').strip()
            if not dept_id:
                return JsonResponse({'status': 'error', 'message': 'Department is required for Department Head role.'})
            department_obj = Department.objects.filter(pk=dept_id, is_active=True).first()
            if not department_obj:
                return JsonResponse({'status': 'error', 'message': 'Invalid department selected.'})

        # ── Warn if removing dept head role with pending approvals ─
        force = request.POST.get('force') == '1'
        if not force and user.role and user.role.name == 'Department Head' and role_obj and role_obj.name != 'Department Head':
            dept = user.department
            if dept:
                has_pending = (
                    OvertimeRequest.objects.filter(status='PENDING', attendance__employee__department=dept).exists() or
                    UndertimeRequest.objects.filter(status='PENDING', attendance__employee__department=dept).exists() or
                    HalfdayRequest.objects.filter(status='PENDING', employee__department=dept).exists() or
                    LeaveRequest.objects.filter(status='PENDING', employee__department=dept).exists() or
                    MissingLog.objects.filter(status='PENDING', employee__department=dept).exists()
                )
                if has_pending:
                    return JsonResponse({
                        'status': 'warning',
                        'message': f'This user has pending approvals in {dept.name}. Changing their role will leave those requests unattended. Proceed?',
                    })

        employee_id  = request.POST.get('employee', '').strip()
        employee_obj = EmployeeModel.objects.filter(pk=employee_id).first() if employee_id else None

        user.role       = role_obj
        user.email      = email
        user.department = department_obj
        user.employee   = employee_obj
        user.save(update_fields=['role', 'email', 'department', 'employee'])

        return JsonResponse({'status': 'updated'})

@method_decorator([permission_required('settings_system_users', 'delete')], name='dispatch')
class SystemUserDeactivateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found.'})

        if user == request.user:
            return JsonResponse({'status': 'error', 'message': 'You cannot deactivate your own account.'})

        user.is_active = False
        user.save(update_fields=['is_active'])

        return JsonResponse({'status': 'deactivated'})

@method_decorator([permission_required('settings_system_users', 'update')], name='dispatch')
class SystemUserReactivateView(LoginRequiredMixin, View):

    def post(self, request):
        user_ids = request.POST.getlist('user_ids')

        if not user_ids:
            return JsonResponse({'status': 'error', 'message': 'No users selected.'})

        updated = User.objects.filter(pk__in=user_ids, is_active=False).update(is_active=True)

        return JsonResponse({'status': 'reactivated', 'count': updated})

# decorator not needed
class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'pages/settings/change_pw.django'
 
    def get(self, request, *args, **kwargs):
        # Capture where the user came from, but not the page itself
        referer = request.META.get('HTTP_REFERER', '')
        if referer and 'change-password' not in referer:
            request.session['pw_change_return'] = referer
        return super().get(request, *args, **kwargs)
 
    def form_valid(self, form):
        # Stay logged in after password change
        update_session_auth_hash(self.request, form.user)

        # Clear the forced-change flag now that the password has actually been updated
        if form.user.must_change_password:
            form.user.must_change_password = False
            form.user.save(update_fields=['must_change_password'])

        return super().form_valid(form)
 
    def get_success_url(self):
        return_url = self.request.session.pop('pw_change_return', None)
        if return_url:
            separator = '&' if '?' in return_url else '?'
            return f"{return_url}{separator}pw_changed=1"
        return reverse_lazy('scanner') + '?pw_changed=1'

@method_decorator([permission_required('settings_system_users', 'update')], name='dispatch')
class SystemUserResetPasswordView(LoginRequiredMixin, View):

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, is_active=True)
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found.'})

        new_password = _generate_password()
        user.set_password(new_password)
        user.save(update_fields=['password'])

        email_sent = True
        try:
            send_mail(
                subject      = 'Your MBPI-QRAS password has been reset',
                message      = (
                    f"Hello {user.first_name},\n\n"
                    f"Your password for the MBPI QR Attendance System has been reset by the System Administrator.\n\n"
                    f"Username : {user.username}\n"
                    f"New Password : {new_password}\n\n"
                    f"Please log in and change your password as soon as possible.\n\n"
                    f"— MBPI-QRAS IT Admin"
                ),
                from_email     = settings.DEFAULT_FROM_EMAIL,
                recipient_list = [user.email],
                fail_silently  = False,
            )
        except Exception:
            email_sent = False

        return JsonResponse({'status': 'reset', 'email_sent': email_sent})
 
 
# ─────────────────────────────────────────────────────────────────
#   ROLES
# ─────────────────────────────────────────────────────────────────
 
 
@method_decorator([permission_required('settings_roles', 'read')], name='dispatch')
class RoleListView(LoginRequiredMixin, ListView):
    model               = Role
    template_name       = 'pages/settings/system_roles.django'
    context_object_name = 'roles'

    def get_queryset(self):
        show_inactive = self.request.GET.get('show_inactive') == 'true'
        return Role.objects.all() if show_inactive else Role.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['show_inactive'] = self.request.GET.get('show_inactive') == 'true'
        return ctx


@method_decorator([permission_required('settings_roles', 'create')], name='dispatch')
class RoleCreateView(LoginRequiredMixin, View):

    def post(self, request):
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Role name is required.'})
        if Role.objects.filter(name__iexact=name).exists():
            return JsonResponse({'status': 'error', 'message': 'A role with that name already exists.'})
        Role.objects.create(name=name)
        return JsonResponse({'status': 'created'})


@method_decorator([permission_required('settings_roles', 'update')], name='dispatch')
class RoleUpdateView(LoginRequiredMixin, View):

    def get(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Role not found.'})

        modules = Module.objects.all()
        perms   = {rp.module_id: rp for rp in role.permissions.select_related('module')}

        data = []
        for module in modules:
            perm = perms.get(module.pk)
            data.append({
                'module_id':   module.pk,
                'module_name': module.name,
                'can_create':  perm.can_create if perm else False,
                'can_read':    perm.can_read   if perm else False,
                'can_update':  perm.can_update if perm else False,
                'can_delete':  perm.can_delete if perm else False,
            })

        return JsonResponse({
            'status':  'ok',
            'role':    {'pk': role.pk, 'name': role.name},
            'modules': data,
        })

    def post(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Role not found.'})

        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Role name is required.'})
        if Role.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            return JsonResponse({'status': 'error', 'message': 'A role with that name already exists.'})

        role.name = name
        role.save(update_fields=['name'])

        for module in Module.objects.all():
            perm, _ = RolePermission.objects.get_or_create(role=role, module=module)
            perm.can_create = request.POST.get(f"m_{module.pk}_create") == '1'
            perm.can_read   = request.POST.get(f"m_{module.pk}_read")   == '1'
            perm.can_update = request.POST.get(f"m_{module.pk}_update") == '1'
            perm.can_delete = request.POST.get(f"m_{module.pk}_delete") == '1'
            perm.save(update_fields=['can_create', 'can_read', 'can_update', 'can_delete'])

        return JsonResponse({'status': 'updated'})


@method_decorator([permission_required('settings_roles', 'delete')], name='dispatch')
class RoleDeactivateView(LoginRequiredMixin, View):

    def post(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Role not found.'})
        if role.name == 'Admin':
            return JsonResponse({'status': 'error', 'message': 'The Admin role cannot be deactivated.'})
        assigned_count = User.objects.filter(role=role, is_active=True).count()
        if assigned_count:
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot deactivate "{role.name}" — {assigned_count} system user(s) are still assigned to this role. Reassign or remove them first.'
            })
        role.is_active = False
        role.save(update_fields=['is_active'])
        return JsonResponse({'status': 'deactivated'})


@method_decorator([permission_required('settings_roles', 'update')], name='dispatch')
class RoleReactivateView(LoginRequiredMixin, View):

    def post(self, request):
        role_ids = request.POST.getlist('role_ids')
        if not role_ids:
            return JsonResponse({'status': 'error', 'message': 'No roles selected.'})
        updated = Role.objects.filter(pk__in=role_ids, is_active=False).update(is_active=True)
        return JsonResponse({'status': 'reactivated', 'count': updated})

@method_decorator([permission_required('settings_roles', 'read')], name='dispatch')
class RoleAssignedUsersView(LoginRequiredMixin, View):

    def get(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Role not found.'})

        users = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        data  = [
            {
                'pk':          u.pk,
                'name':        f"{u.last_name}, {u.first_name}",
                'assigned_as': u.role.name if u.role else 'None',
                'in_role':     u.role_id == role.pk,
            }
            for u in users
        ]

        return JsonResponse({'status': 'ok', 'role': {'pk': role.pk, 'name': role.name}, 'users': data})

    def post(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Role not found.'})

        user_ids = request.POST.getlist('user_ids')

        # Unassign users currently in this role who were unchecked
        User.objects.filter(role=role).exclude(pk__in=user_ids).update(role=None)

        # Assign checked users to this role
        if user_ids:
            User.objects.filter(pk__in=user_ids).update(role=role)

        return JsonResponse({'status': 'updated'})


@method_decorator([login_required], name='dispatch')
class OnlineUsersView(LoginRequiredMixin, View):
    def get(self, request):
        logged_in_ids = set(
            User.objects.filter(is_online=True).values_list('pk', flat=True)
        )
        return JsonResponse({'online': logged_in_ids})
