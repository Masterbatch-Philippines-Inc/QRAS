from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from apps.qras.modules.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from .utils import get_clock_offset, set_clock_offset
from django.conf import settings
from django.contrib.auth import authenticate
import time as time_module

LOCKOUT_ENABLED = True
LOCKOUT_MAX_ATTEMPTS = 3
LOCKOUT_DURATION_SECONDS = 120

_co_lockout_store = {}

def _co_get_lockout(user_id):
    return _co_lockout_store.setdefault(user_id, {'attempts': 0, 'locked_until': None})

def _co_reset_lockout(user_id):
    _co_lockout_store[user_id] = {'attempts': 0, 'locked_until': None}


@method_decorator(permission_required('settings_system_users', 'read'), name='dispatch')
class ClockOffsetView(View):
    template_name = 'pages/features/offset.django'

    def get(self, request):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('login')
        role = getattr(request.user, 'role', None)
        if not role or role.name != settings.ADMIN_ROLE_NAME:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()
        return render(request, self.template_name, {
            'current_offset': get_clock_offset(),
            'already_verified': False,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        role = getattr(request.user, 'role', None)
        if not role or role.name != settings.ADMIN_ROLE_NAME:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        try:
            minutes = int(request.POST.get('minutes', 0))
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid value'}, status=400)
        set_clock_offset(minutes)
        return JsonResponse({'status': 'ok', 'offset': minutes})


@method_decorator(permission_required('settings_system_users', 'read'), name='dispatch')
class VerifyClockOffsetPasswordView(View):
    def post(self, request):
        user_id = request.user.id
        record  = _co_get_lockout(user_id)

        if LOCKOUT_ENABLED and record['locked_until']:
            remaining = record['locked_until'] - time_module.time()
            if remaining > 0:
                return JsonResponse({'status': 'locked', 'remaining': int(remaining)})
            else:
                _co_reset_lockout(user_id)
                record = _co_get_lockout(user_id)

        password = request.POST.get('password', '')
        user     = authenticate(request, username=request.user.username, password=password)

        if user is not None:
            _co_reset_lockout(user_id)
            return JsonResponse({'status': 'ok'})
        else:
            record['attempts'] += 1
            attempts_left = LOCKOUT_MAX_ATTEMPTS - record['attempts']

            if LOCKOUT_ENABLED and record['attempts'] >= LOCKOUT_MAX_ATTEMPTS:
                record['locked_until'] = time_module.time() + LOCKOUT_DURATION_SECONDS
                return JsonResponse({'status': 'locked', 'remaining': LOCKOUT_DURATION_SECONDS})

            return JsonResponse({'status': 'invalid', 'attempts_left': attempts_left})