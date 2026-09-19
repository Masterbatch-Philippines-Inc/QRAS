import secrets
import string

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from apps.qras.models.auth import User
from django.utils.decorators import method_decorator


# ─────────────────────────────────────────────────────────────────
#   EXISTING VIEWS
# ─────────────────────────────────────────────────────────────────

def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            user.is_online = True
            user.save(update_fields=['is_online'])
            # if user.must_change_password:
            #     return redirect('change-password')
            return redirect('dashboard')
        else:
            return render(request, "pages/auth/login.django", {'error': 'Invalid username or password.'})
    return render(request, "pages/auth/login.django")

def logout_view(request):
    if request.user.is_authenticated:
        request.user.is_online = False
        request.user.save(update_fields=['is_online'])
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────────────────────────────
#   HELPERS
# ─────────────────────────────────────────────────────────────────

def _generate_password(length=12):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Remove characters that are commonly confusing or cause email issues
    alphabet = ''.join(c for c in alphabet if c not in '"\'\\`|<>')
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _generate_username(first_name, last_name):
    """
    Builds: first initial + last name, lowercased, spaces stripped.
    Appends a counter if the username already exists.
    """
    base     = (first_name[0] + '_' + last_name).lower().replace(' ', '')
    username = base
    counter  = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1
    return username


@method_decorator([login_required], name='dispatch')
class CheckPasswordView(View):
    def post(self, request):
        password = request.POST.get('password', '')
        if request.user.check_password(password):
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'error', 'message': 'Incorrect password.'})