from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from apps.qras.modules.auth.decorators import permission_required
from apps.qras.handlers.utils.sync_helpers import sync_all_models, sync_scan_files, is_auto_sync_enabled, set_auto_sync_enabled
import io
from django.http import StreamingHttpResponse
import threading
import uuid
import time as time_module

# Create your views here.
def maintenance(request):
    return render(request, 'handlers/maintenance.html')

def error_401(request):
    return render(request, 'handlers/error-401.html', status=401)

def error_403(request, exception=None):
    return render(request, 'handlers/error-403.html', status=403)

def error_404(request, exception=None):
    return render(request, 'handlers/error-404.html', status=404)

def error_500(request):
    return render(request, 'handlers/error-500.html', status=500)

# In-memory sync job store { job_id: { 'lines': [], 'done': bool } }
_sync_jobs = {}

# Set to False to disable lockout entirely during development
LOCKOUT_ENABLED = True
LOCKOUT_MAX_ATTEMPTS = 3
LOCKOUT_DURATION_SECONDS = 120  # 2 minutes

# In-memory lockout store { user_id: { 'attempts': int, 'locked_until': float|None } }
_lockout_store = {}


def _get_lockout(user_id):
    return _lockout_store.setdefault(user_id, {'attempts': 0, 'locked_until': None})


def _reset_lockout(user_id):
    _lockout_store[user_id] = {'attempts': 0, 'locked_until': None}

def _run_sync(job_id):
    job = _sync_jobs[job_id]

    class FakeStyle:
        def SUCCESS(self, msg): return f'[SUCCESS] {msg}'
        def WARNING(self, msg): return f'[WARNING] {msg}'
        def ERROR(self, msg):   return f'[ERROR] {msg}'

    class FakeStdout:
        def write(self, msg):
            job['lines'].append(msg)

    stdout = FakeStdout()
    style  = FakeStyle()

    try:
        job['lines'].append('[INFO] Starting sync...')
        sync_all_models(stdout, style)
        sync_scan_files(stdout, style)
        job['lines'].append('[INFO] Sync completed.')
    except Exception as e:
        job['lines'].append(f'[ERROR] {str(e)}')
    finally:
        job['done'] = True


@method_decorator(permission_required('settings_system_users', 'read'), name='dispatch')
class TriggerManualSyncView(View):
    def post(self, request):
        job_id = str(uuid.uuid4())
        _sync_jobs[job_id] = {'lines': [], 'done': False}
        thread = threading.Thread(target=_run_sync, args=(job_id,), daemon=True)
        thread.start()
        return JsonResponse({'status': 'ok', 'job_id': job_id})


@method_decorator(permission_required('settings_system_users', 'read'), name='dispatch')
class SyncStatusView(View):
    def get(self, request):
        job_id = request.GET.get('job_id')
        if not job_id or job_id not in _sync_jobs:
            return JsonResponse({'status': 'error', 'error': 'Invalid job ID.'}, status=400)

        job    = _sync_jobs[job_id]
        cursor = int(request.GET.get('cursor', 0))
        new_lines = job['lines'][cursor:]

        return JsonResponse({
            'status': 'ok',
            'lines':  new_lines,
            'cursor': cursor + len(new_lines),
            'done':   job['done'],
        })

@method_decorator(permission_required('settings_system_users', 'read'), name='dispatch')
class VerifySyncPasswordView(View):
    def post(self, request):
        from django.contrib.auth import authenticate

        user_id = request.user.id
        record  = _get_lockout(user_id)

        # Check lockout
        if LOCKOUT_ENABLED and record['locked_until']:
            remaining = record['locked_until'] - time_module.time()
            if remaining > 0:
                return JsonResponse({
                    'status':    'locked',
                    'remaining': int(remaining),
                })
            else:
                _reset_lockout(user_id)
                record = _get_lockout(user_id)

        password = request.POST.get('password', '')
        user     = authenticate(request, username=request.user.username, password=password)

        if user is not None:
            _reset_lockout(user_id)
            request.session['sync_verified'] = True
            return JsonResponse({'status': 'ok'})
        else:
            record['attempts'] += 1
            attempts_left = LOCKOUT_MAX_ATTEMPTS - record['attempts']

            if LOCKOUT_ENABLED and record['attempts'] >= LOCKOUT_MAX_ATTEMPTS:
                record['locked_until'] = time_module.time() + LOCKOUT_DURATION_SECONDS
                return JsonResponse({
                    'status':    'locked',
                    'remaining': LOCKOUT_DURATION_SECONDS,
                })

            return JsonResponse({
                'status':        'invalid',
                'attempts_left': attempts_left,
            })

@method_decorator(permission_required('settings_system_users', 'read'), name='dispatch')
class DatabaseSyncView(View):
    def get(self, request):
        already_verified = request.session.get('sync_verified', False)
        return render(request, 'pages/settings/db_sync.django', {
            'already_verified': already_verified,
            'auto_sync_enabled': is_auto_sync_enabled(),
        })


@method_decorator(permission_required('settings_system_users', 'update'), name='dispatch')
class ToggleAutoSyncView(View):
    def post(self, request):
        current = is_auto_sync_enabled()
        set_auto_sync_enabled(not current)
        return JsonResponse({'status': 'ok', 'auto_sync_enabled': not current})




from datetime import datetime, timezone as dt_timezone
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone


def _resolve_since(since_iso):
    try:
        since = datetime.fromisoformat(since_iso.replace('Z', '+00:00'))
        if since.tzinfo is None:
            since = since.replace(tzinfo=dt_timezone.utc)
        return since
    except Exception:
        return timezone.now()


def _resolve_dept(user):
    role = getattr(user, 'role', None)
    if role and role.name == 'Department Head':
        return getattr(user, 'department', None)
    return None


@login_required
def attendance_rows_sse(request):
    from apps.qras.handlers.sse.stream import event_stream_attendance
    since = _resolve_since(request.GET.get('since', timezone.now().isoformat()))
    dept  = _resolve_dept(request.user)
    response = StreamingHttpResponse(
        event_stream_attendance(since, dept, request.user),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
def attendance_sse(request):
    from apps.qras.handlers.sse.stream import event_stream
    since = _resolve_since(request.GET.get('since', timezone.now().isoformat()))
    dept  = _resolve_dept(request.user)
    response = StreamingHttpResponse(
        event_stream(since, dept, request.user),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response