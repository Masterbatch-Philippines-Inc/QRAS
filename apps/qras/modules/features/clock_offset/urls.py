from django.urls import path
from .views import ClockOffsetView, VerifyClockOffsetPasswordView

urlpatterns = [
    path('c.o./', ClockOffsetView.as_view(), name='clock_offset'),
    path('c.o./verify-password/', VerifyClockOffsetPasswordView.as_view(), name='verify-clock-offset-password'),
]