import os
import shutil
import logging
from django.conf import settings
from decouple import config, Config, RepositoryEnv

logger = logging.getLogger(__name__)

_ENV_PATH = os.path.join(settings.BASE_DIR, '.env')


def is_auto_sync_enabled():
    """Reads AUTO_SYNC_ENABLED fresh from .env every call (bypasses decouple's cache)."""
    try:
        fresh_config = Config(RepositoryEnv(_ENV_PATH))
        return fresh_config('AUTO_SYNC_ENABLED', default=True, cast=bool)
    except Exception as e:
        print(f'[AutoSync] Could not read AUTO_SYNC_ENABLED, defaulting to True: {e}')
        logger.warning(f'[AutoSync] Could not read AUTO_SYNC_ENABLED, defaulting to True: {e}')
        return True


def set_auto_sync_enabled(value: bool):
    """Persists AUTO_SYNC_ENABLED to .env, updating the line if present or appending it."""
    new_value = 'True' if value else 'False'
    lines = []
    found = False

    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, 'r') as f:
            lines = f.readlines()

    for i, line in enumerate(lines):
        if line.strip().startswith('AUTO_SYNC_ENABLED='):
            lines[i] = f'AUTO_SYNC_ENABLED={new_value}\n'
            found = True
            break

    if not found:
        lines.append(f'AUTO_SYNC_ENABLED={new_value}\n')

    with open(_ENV_PATH, 'w') as f:
        f.writelines(lines)

def _get_server_media_scans_paths():
    base = config('SERVER_DEPLOYMENT_BASE')
    active_txt = os.path.join(base, 'active.txt')

    slots = {
        'blue':  None,
        'green': None,
    }

    for slot in slots:
        slot_dir = os.path.join(base, slot)
        candidate = os.path.join(slot_dir, 'core', 'media', 'scans')
        if os.path.isdir(slot_dir):
            slots[slot] = candidate

    return [path for path in slots.values() if path]

def sync_model(model, label, stdout, style):
    local_records = model.objects.using('default').all()
    synced = 0
    skipped = 0
    for record in local_records:
        try:
            if not model.objects.using('server').filter(id=record.id).exists():
                record.save(using='server')
                synced += 1
        except Exception as e:
            logger.warning(f'[{label}] Skipped ID {record.id}: {e}')
            skipped += 1
    stdout.write(style.SUCCESS(f'Successfully synced {synced} new {label} record(s).'))
    if skipped:
        stdout.write(style.WARNING(f'  → {skipped} {label} record(s) skipped (already exists or FK error — check logs).'))


def sync_all_models(stdout, style):
    from app.authentication.models import Role, Module, RolePermission
    from app.employees.models import (
        Department, Position, EmployeeGroup, Employee,
        EmployeeGroupMembership, EmployeeContact, EmployeeGovernmentID,
        EmployeeDetails, EmployeeSchedule
    )
    from app.authentication.models import User
    from app.schedules.models import ShiftSchedule, ScheduleActivityLog
    from app.attendance.models import (
        Attendance, AttendanceStatus, AttendanceLog, AttendanceLogAudit,
        Holiday, OvertimeRequest, UndertimeRequest, HalfdayRequest,
        LeaveRequest, AbsenceExcusal, EmployeeRestDay, MissingLog
    )
    from app.scanner.models import ScanCapture

    sync_order = [
        (Department,              'Department'),
        (Position,                'Position'),
        (EmployeeGroup,           'EmployeeGroup'),
        (Role,                    'Role'),
        (Module,                  'Module'),
        (RolePermission,          'RolePermission'),
        (Employee,                'Employee'),
        (EmployeeContact,         'EmployeeContact'),
        (EmployeeGovernmentID,    'EmployeeGovernmentID'),
        (EmployeeDetails,         'EmployeeDetails'),
        (EmployeeGroupMembership, 'EmployeeGroupMembership'),
        (EmployeeSchedule,        'EmployeeSchedule'),
        (User,                    'User'),
        (ShiftSchedule,           'ShiftSchedule'),
        (ScheduleActivityLog,     'ScheduleActivityLog'),
        (Attendance,              'Attendance'),
        (AttendanceStatus,        'AttendanceStatus'),
        (AttendanceLog,           'AttendanceLog'),
        (AttendanceLogAudit,      'AttendanceLogAudit'),
        (Holiday,                 'Holiday'),
        (OvertimeRequest,         'OvertimeRequest'),
        (UndertimeRequest,        'UndertimeRequest'),
        (HalfdayRequest,          'HalfdayRequest'),
        (LeaveRequest,            'LeaveRequest'),
        (AbsenceExcusal,          'AbsenceExcusal'),
        (EmployeeRestDay,         'EmployeeRestDay'),
        (MissingLog,              'MissingLog'),
        (ScanCapture,             'ScanCapture'),
    ]

    for model, label in sync_order:
        sync_model(model, label, stdout, style)


def sync_scan_files(stdout, style):
    local_scans = os.path.join(settings.MEDIA_ROOT, 'scans')

    if not os.path.exists(local_scans):
        stdout.write(style.WARNING('Local media/scans directory not found. Skipping file sync.'))
        return

    targets = _get_server_media_scans_paths()

    if not targets:
        stdout.write(style.WARNING(
            'Could not resolve any server media/scans paths. '
            'Ensure \\\\system-server is online and deployment folders exist. Skipping file sync.'
        ))
        return

    for server_scans in targets:
        if not os.path.exists(server_scans):
            stdout.write(style.WARNING(f'[ScanFiles] Skipping unreachable path: {server_scans}'))
            continue

        copied = 0
        skipped = 0

        for root, dirs, files in os.walk(local_scans):
            relative_root = os.path.relpath(root, local_scans)
            target_dir = os.path.join(server_scans, relative_root)
            os.makedirs(target_dir, exist_ok=True)

            for filename in files:
                src = os.path.join(root, filename)
                dst = os.path.join(target_dir, filename)
                if not os.path.exists(dst):
                    try:
                        shutil.copy2(src, dst)
                        copied += 1
                    except Exception as e:
                        logger.warning(f'[ScanFiles] Failed to copy {src}: {e}')
                        skipped += 1
                else:
                    skipped += 1

        stdout.write(style.SUCCESS(f'[ScanFiles] {server_scans} → Copied: {copied}, Already exists (skipped): {skipped}'))