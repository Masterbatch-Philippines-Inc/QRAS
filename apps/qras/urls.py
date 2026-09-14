from django.urls import path
# from . import views
from .modules.attendance.views import *
from .modules.dashboard.views import *
from .modules.request.views import *
from .modules.scanner.views import *
from .modules.attendance.live_updates import *

urlpatterns = [
    # path('',                                     views.login_view,                          name='login'),
    # path('logout/',                              views.logout_view,                         name='logout'),
    path('attendance',                           AttendanceRecordView.as_view(),            name='attendance-records'),
    path('attendance/logs/',                     EmployeeAttendanceLogsView.as_view(),      name='employee-attendance-logs'),
    path('attendance/live-updates/',             AttendanceLiveUpdateView.as_view(),        name='attendance-live-updates'),
    path('manual-attendance',                    ManualAttendanceView.as_view(),            name='manual-attendance'),
    path('manual-attendance/overwrite/',         ManualOverwriteAttendanceView.as_view(),   name='manual-overwrite-attendance'),
    path('dashboard',                            DashboardView.as_view(),                   name='dashboard'),
    path('overtime/filing/',                     OTFilingView.as_view(),                    name='ot_filing'),
    path('overtime/logs/',                       OTLogsView.as_view(),                      name='ot_logs'),
    path('overtime/',                            OTDecisionView.as_view(),                  name='ot_decision'),
    path('undertime/decision/',                  UTDecisionView.as_view(),                  name='ut_decision'),
    path('halfday/decision/',                    HDDecisionView.as_view(),                  name='hd_decision'),
    path('leave/decision/',                      LeaveDecisionView.as_view(),               name='lv-decision'),
    path('leave/filing/',                        LeaveFilingView.as_view(),                 name='leave-filing'),
    path('leave/compute-days/',                  LeaveComputeDaysView.as_view(),            name='leave-compute-days'),
    path('attendance/rest-days/',                EmployeeRestDayView.as_view(),             name='employee-rest-days'),
    path('attendance/rest-days/manage/',         RestDayManagementView.as_view(),           name='rest-days-manage'),
    path('attendance/missing-logs/',             MissingLogView.as_view(),                  name='missing-logs'),
    # path('scan-upload',                          ScanUploadView.as_view(),                  name='scan-upload'),
    # path('scan-upload/parse/',                   ScanUploadParseView.as_view(),             name='scan-upload-parse'),
    # path('scan-upload/save/',                    ScanUploadSaveView.as_view(),              name='scan-upload-save'),
]