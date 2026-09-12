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
    from handlers.sse.stream import event_stream_attendance
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
    from handlers.sse.stream import event_stream
    since = _resolve_since(request.GET.get('since', timezone.now().isoformat()))
    dept  = _resolve_dept(request.user)
    response = StreamingHttpResponse(
        event_stream(since, dept, request.user),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response