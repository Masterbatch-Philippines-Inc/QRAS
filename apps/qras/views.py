from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        return render(request, "pages/auth/login.django", {
            "error": "Invalid username or password."
        })
    return render(request, "pages/auth/login.django")

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard_view(request):
    return render(request, "pages/dashboard.django")


from .view.attendance import (
    AttendanceRecordView,
    EmployeeAttendanceLogsView,
    ManualAttendanceView,
    EmployeeRestDayView,
    RestDayManagementView,
    MissingLogView,
    ManualOverwriteAttendanceView,
)
from .view.dashboard import (
    Dashboard
)
from .view.request import (
    OTFilingView,
    OTLogsView,
    OTDecisionView,
    UTDecisionView,
    HDDecisionView,
    LeaveFilingView, 
    LeaveDecisionView,
    LeaveComputeDaysView
)

from .modules.attendance.views.scan_upload import (
    ScanUploadView,
    ScanUploadParseView,
    ScanUploadSaveView,
)

from .modules.attendance.views.live_updates import (
    AttendanceLiveUpdateView
)