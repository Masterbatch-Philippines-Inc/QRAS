# from django.core.management.base import BaseCommand
# from django.db import transaction, connection


# DEPARTMENTS = [
#     ('IT',                      'MQRI261'),
#     ('Administration',          'MQRI262'),
#     ('Warehouse',               'MQRI263'),
#     ('Manufacturing Operation', 'MQRI264'),
#     ('Laboratory',              'MQRI265'),
#     ('Maintenance',             'MQRI266'),
#     ('Administrative',          'MQRI267'),
# ]

# POSITIONS = {
#     'Administration': [
#         'HR/QMS/DCC Officer in Charge',
#         'Safety Personnel',
#         'Utility Personnel',
#     ],
#     'Administrative': [
#         'Messenger',
#     ],
#     'IT': [
#         'IT Consultant',
#         'IT Programmer / Data Analyst',
#     ],
#     'Laboratory': [
#         'Chemist / R&D Assistant',
#         'Laboratory Assistant',
#         'Laboratory Head',
#         'Laboratory Manager',
#         'Laboratory Operator',
#         'Laboratory Technician',
#         'Quality Analyst',
#         'R&D Assistant',
#         'Sr. Technical Advisor (Prod. & Lab)',
#     ],
#     'Maintenance': [
#         'Maintenance Facility Manager',
#         'Maintenance Technician',
#     ],
#     'Manufacturing Operation': [
#         'Company Driver',
#         'Production Head',
#         'Production Helper',
#         'Production Maintenance Engineer',
#         'Production Maintenance Tech',
#         'Production Operator',
#         'Production Staff',
#         'Production Supervisor',
#     ],
#     'Warehouse': [
#         'FG Team Leader',
#         'Warehouse Driver',
#         'Warehouse Head',
#         'Warehouse Manager',
#         'Warehouse Personnel',
#         'Warehouse Encoder',
#     ],
# }

# MODULES = [
#     ( 1, 'Scanner',                   'scanner'),
#     ( 2, 'Dashboard',                 'dashboard'),
#     ( 3, 'Attendance',                'attendance'),
#     ( 4, 'Employees',                 'employees'),
#     ( 5, 'Schedules',                 'schedules'),
#     ( 6, 'Unscheduled',               'unscheduled'),
#     ( 7, 'Absences',                  'absences'),
#     ( 8, 'Overtime Approvals',        'approvals_overtime'),
#     ( 9, 'Undertime Approvals',       'approvals_undertime'),
#     (10, 'Half Day Approvals',        'approvals_halfday'),
#     (11, 'Leave Approvals',           'approvals_leaves'),
#     (12, 'Missing Logs',              'approvals_missing_logs'),
#     (13, 'OT Filing',                 'ot_filing'),
#     (14, 'Leave Filing',              'leave_filing'),
#     (15, 'Timesheet (Total)',         'reports_timesheet_total'),
#     (16, 'Timesheet (Actual)',        'reports_timesheet_actual'),
#     (17, 'Departments',               'settings_departments'),
#     (18, 'Dept. Positions',           'settings_positions'),
#     (19, 'Employee Groups',           'settings_employee_groups'),
#     (20, 'Manual Attendance',         'settings_manual_attendance'),
#     (21, 'Smart Manual Attendance',   'settings_smart_manual_attendance'),
#     (22, 'Personal Rest Days',        'settings_personal_rest_days'),
#     (23, 'Roles',                     'settings_roles'),
#     (24, 'System Users',              'settings_system_users'),
# ]

# # role_name: { module_code: (can_create, can_read, can_update, can_delete) }
# ROLE_PERMISSIONS = {
#     'Administrator': 'FULL',  # special case — full access to every module
#     'Department Head': {
#         'dashboard':             (False, True,  False, False),
#         'attendance':            (False, True,  False, False),
#         'employees':             (False, True,  False, False),
#         'schedules':             (False, True,  False, False),
#         'approvals_missing_logs': (False, True,  True,  False),
#     },
#     'Staff': {
#         'dashboard': (False, True, False, False),
#     },
# }

# ADMIN_USERNAME = 'esa'
# ADMIN_EMAIL    = 'dan.mbpi@gmail.com'
# ADMIN_PASSWORD = 'mbpi@2026'


# class Command(BaseCommand):
#     help = 'Seeds critical reference data: departments, positions, modules, roles, permissions, and the default admin account. Safe to re-run.'

#     def handle(self, *args, **options):
#         with transaction.atomic():
#             self.seed_departments()
#             self.seed_positions()
#             self.seed_modules()
#             self.seed_roles_and_permissions()
#             self.seed_admin_account()
#             self.seed_notify_trigger()

#         self.stdout.write(self.style.SUCCESS('Initial data seeding complete.'))

#     def seed_departments(self):
#         from app.employees.models import Department

#         for name, code in DEPARTMENTS:
#             obj, created = Department.objects.get_or_create(
#                 name=name,
#                 defaults={'code': code, 'is_active': True},
#             )
#             if created:
#                 self.stdout.write(self.style.SUCCESS(f'[Department] Created: {name}'))
#             else:
#                 self.stdout.write(f'[Department] Already exists: {name}')

#     def seed_positions(self):
#         from app.employees.models import Department, Position

#         for dept_name, titles in POSITIONS.items():
#             try:
#                 department = Department.objects.get(name=dept_name)
#             except Department.DoesNotExist:
#                 self.stdout.write(self.style.WARNING(
#                     f'[Position] Skipped all positions for "{dept_name}" — department not found.'
#                 ))
#                 continue

#             for title in titles:
#                 obj, created = Position.objects.get_or_create(
#                     title=title,
#                     department=department,
#                     defaults={'is_active': True},
#                 )
#                 if created:
#                     self.stdout.write(self.style.SUCCESS(f'[Position] Created: {title} ({dept_name})'))
#                 else:
#                     self.stdout.write(f'[Position] Already exists: {title} ({dept_name})')

#     def seed_modules(self):
#         from app.authentication.models import Module

#         for order, name, code in MODULES:
#             obj, created = Module.objects.get_or_create(
#                 code=code,
#                 defaults={'name': name, 'order': order},
#             )
#             if created:
#                 self.stdout.write(self.style.SUCCESS(f'[Module] Created: {name}'))
#             else:
#                 self.stdout.write(f'[Module] Already exists: {name}')

#     def seed_roles_and_permissions(self):
#         from app.authentication.models import Role, Module, RolePermission

#         for role_name, perms in ROLE_PERMISSIONS.items():
#             role, created = Role.objects.get_or_create(name=role_name)
#             if created:
#                 self.stdout.write(self.style.SUCCESS(f'[Role] Created: {role_name}'))
#             else:
#                 self.stdout.write(f'[Role] Already exists: {role_name}')

#             if perms == 'FULL':
#                 for module in Module.objects.all():
#                     RolePermission.objects.update_or_create(
#                         role=role,
#                         module=module,
#                         defaults={
#                             'can_create': True,
#                             'can_read':   True,
#                             'can_update': True,
#                             'can_delete': True,
#                         },
#                     )
#                 self.stdout.write(self.style.SUCCESS(f'[Permissions] {role_name} granted full access.'))
#                 continue

#             for module_code, (c, r, u, d) in perms.items():
#                 try:
#                     module = Module.objects.get(code=module_code)
#                 except Module.DoesNotExist:
#                     self.stdout.write(self.style.WARNING(
#                         f'[Permissions] Skipped "{module_code}" for {role_name} — module not found.'
#                     ))
#                     continue

#                 RolePermission.objects.update_or_create(
#                     role=role,
#                     module=module,
#                     defaults={
#                         'can_create': c,
#                         'can_read':   r,
#                         'can_update': u,
#                         'can_delete': d,
#                     },
#                 )
#             self.stdout.write(self.style.SUCCESS(f'[Permissions] Applied for {role_name}.'))

#     def seed_admin_account(self):
#         from app.authentication.models import User, Role

#         admin_role = Role.objects.get(name='Administrator')

#         user, created = User.objects.get_or_create(
#             username=ADMIN_USERNAME,
#             defaults={
#                 'email':      ADMIN_EMAIL,
#                 'first_name': 'Admin',
#                 'last_name':  'Account',
#                 'role':       admin_role,
#                 'is_staff':   True,
#                 'must_change_password': True,
#             },
#         )

#         if created:
#             user.set_password(ADMIN_PASSWORD)
#             user.save()
#             self.stdout.write(self.style.SUCCESS(
#                 f'[Admin] Created account "{ADMIN_USERNAME}" with a temporary password. Must change password on first login.'
#             ))
#         else:
#             self.stdout.write(f'[Admin] Account "{ADMIN_USERNAME}" already exists — left untouched.')
    
#     def seed_notify_trigger(self):
#         with connection.cursor() as cursor:
#             # ── Remove the old, now-redundant attendance-only trigger/function ──
#             cursor.execute("""
#                 DROP TRIGGER IF EXISTS attendance_log_notify ON attendance_attendancelog;
#                 DROP FUNCTION IF EXISTS notify_attendance_change();
#             """)

#             # ── Single consolidated trigger, covering all sync-tracked tables ──
#             cursor.execute("""
#                 CREATE OR REPLACE FUNCTION notify_sync_needed()
#                 RETURNS trigger AS $$
#                 BEGIN
#                     PERFORM pg_notify('sync_needed', TG_TABLE_NAME);
#                     RETURN NEW;
#                 END;
#                 $$ LANGUAGE plpgsql;

#                 DO $$
#                 DECLARE
#                     t TEXT;
#                 BEGIN
#                     FOREACH t IN ARRAY ARRAY[
#                         'attendance_attendancelog',
#                         'attendance_attendance',
#                         'attendance_attendancestatus',
#                         'attendance_attendancelogaudit',
#                         'scanner_scancapture',
#                         'employees_employee',
#                         'employees_employeeschedule'
#                     ]
#                     LOOP
#                         EXECUTE format(
#                             'DROP TRIGGER IF EXISTS trg_sync_%s ON %I;
#                              CREATE TRIGGER trg_sync_%s
#                              AFTER INSERT OR UPDATE ON %I
#                              FOR EACH ROW EXECUTE FUNCTION notify_sync_needed();',
#                             t, t, t, t
#                         );
#                     END LOOP;
#                 END;
#                 $$;
#             """)

#         self.stdout.write(self.style.SUCCESS(
#             '[Trigger] Consolidated: notify_sync_needed() with trg_sync_* on all 7 sync-tracked tables. '
#             'Old attendance_log_notify trigger removed.'
#         ))