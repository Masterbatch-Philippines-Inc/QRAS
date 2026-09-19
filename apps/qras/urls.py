from django.urls import path
from .handlers.views import *
from .modules.attendance.live_updates import *
from .modules.attendance.views import *
from .modules.auth.views import *
from .modules.dashboard.views import *
from .modules.employee.views import *
from .modules.report.views import *
from .modules.request.views import *
from .modules.settings.views import *
from .modules.scanner.views import *
from .modules.schedules.views import *

urlpatterns = [
    # ── Authentication ────────────────────────────────────────────
    path('',                                        login_view,                                 name='login'),
    path('logout/',                                 logout_view,                                name='logout'),
    
    # ── System Users ──────────────────────────────────────────────
    path('system-users/',                           SystemUserListView.as_view(),               name='system-users'),
    path('system-users/create/',                    SystemUserCreateView.as_view(),             name='system-users-create'),
    path('system-users/<int:pk>/update/',           SystemUserUpdateView.as_view(),             name='system-users-update'),
    path('system-users/<int:pk>/deactivate/',       SystemUserDeactivateView.as_view(),         name='system-users-deactivate'),
    path('system-users/reactivate/',                SystemUserReactivateView.as_view(),         name='system-users-reactivate'),
    path('change-password/',                        CustomPasswordChangeView.as_view(),         name='change-password'),
    path('system-users/<int:pk>/reset-password/',   SystemUserResetPasswordView.as_view(),      name='system-users-reset-password'),
    
    # ── System Roles ──────────────────────────────────────────────
    path('roles/',                                  RoleListView.as_view(),                     name='role-list'),
    path('roles/create/',                           RoleCreateView.as_view(),                   name='role-create'),
    path('roles/<int:pk>/update/',                  RoleUpdateView.as_view(),                   name='role-update'),
    path('roles/<int:pk>/deactivate/',              RoleDeactivateView.as_view(),               name='role-deactivate'),
    path('roles/reactivate/',                       RoleReactivateView.as_view(),               name='role-reactivate'),
    path('roles/<int:pk>/users/',                   RoleAssignedUsersView.as_view(),            name='role-users'),
    
    # ── Log Stat ──────────────────────────────────────────────────
    path('auth/online-users/',                      OnlineUsersView.as_view(),                  name='online-users'),
    path('auth/check-password/',                    CheckPasswordView.as_view(),                name='check-password'), 
    
    path('attendance',                              AttendanceRecordView.as_view(),             name='attendance-records'),
    path('attendance/logs/',                        EmployeeAttendanceLogsView.as_view(),       name='employee-attendance-logs'),
    path('attendance/live-updates/',                AttendanceLiveUpdateView.as_view(),         name='attendance-live-updates'),
    path('manual-attendance',                       ManualAttendanceView.as_view(),             name='manual-attendance'),
    path('manual-attendance/overwrite/',            ManualOverwriteAttendanceView.as_view(),    name='manual-overwrite-attendance'),
    path('dashboard',                               DashboardView.as_view(),                    name='dashboard'),
    # path('overtime/filing/',                        OTFilingView.as_view(),                     name='ot_filing'),
    path('overtime/logs/',                          OTLogsView.as_view(),                       name='ot_logs'),
    path('overtime/',                               OTDecisionView.as_view(),                   name='ot_decision'),
    path('undertime/decision/',                     UTDecisionView.as_view(),                   name='ut_decision'),
    path('halfday/decision/',                       HDDecisionView.as_view(),                   name='hd_decision'),
    path('leave/decision/',                         LeaveDecisionView.as_view(),                name='lv-decision'),
    # path('leave/filing/',                           LeaveFilingView.as_view(),                  name='leave-filing'),
    path('leave/compute-days/',                     LeaveComputeDaysView.as_view(),             name='leave-compute-days'),
    path('attendance/rest-days/',                   EmployeeRestDayView.as_view(),              name='employee-rest-days'),
    path('attendance/rest-days/manage/',            RestDayManagementView.as_view(),            name='rest-days-manage'),
    path('attendance/missing-logs/',                MissingLogView.as_view(),                   name='missing-logs'),
    
    
    path('scan-upload',                             ScanUploadView.as_view(),                   name='scan-upload'),
    path('scan-upload/parse/',                      ScanUploadParseView.as_view(),              name='scan-upload-parse'),
    path('scan-upload/save/',                       ScanUploadSaveView.as_view(),               name='scan-upload-save'),
    
    path('401/',                                    error_401,                                  name='error-401'),
    path('403/',                                    error_403,                                  name='error-403'),
    path('404/',                                    error_404,                                  name='error-404'),
    path('500/',                                    error_500,                                  name='error-500'),
    path('maintenance',                             maintenance,                                name='maintenance'),
    path('manual-sync/',                            TriggerManualSyncView.as_view(),            name='manual-sync'),
    path('toggle-auto-sync/',                       ToggleAutoSyncView.as_view(),               name='toggle-auto-sync'),
    path('sync-status/',                            SyncStatusView.as_view(),                   name='sync-status'),
    path('verify-sync-password/',                   VerifySyncPasswordView.as_view(),           name='verify-sync-password'),
    path('database-sync/',                          DatabaseSyncView.as_view(),                 name='database-sync'),
    path('sse/attendance/',                         attendance_sse,                             name='sse_attendance'),
    path('sse/attendance-rows/',                    attendance_rows_sse,                        name='sse_attendance_rows'),
    
    
    path('scanner',                                     ScanAttendanceView.as_view(),           name='scanner'),
    path('employee-code',                               EmployeeCodeView.as_view(),             name='employee-code'),
    path('employee-code/lookup/<int:employee_id>/',     EmployeeLookupView.as_view(),           name='employee-lookup'),
    path('scan-attendance',                             ScanAttendanceView.as_view(),           name='scan-attendance'),
    path('overwrite-attendance',                        UpdateAttendanceView.as_view(),         name='overwrite-attendance'),
    path('scan-captures',                               ScanCaptureListView.as_view(),          name='scan-captures'),
    path('scan-captures/data/<int:employee_id>/',       ScanCaptureDataView.as_view(),          name='scan-captures-data'),
    path('scan-captures/summary/',                      ScanCaptureSummaryView.as_view(),       name='scan-captures-summary'),
    path('check-time-in-status/',                       CheckTimeInStatusView.as_view(),        name='check-time-in-status'),
    

    # ── Employees ──────────────────────────────────────────────────
    path('employees',                               EmployeeListView.as_view(),                 name='employee-records'),
    path('employees/add',                           EmployeeCreateView.as_view(),               name='add-employee'),
    path('employees/<int:pk>/update',               EmployeeUpdateView.as_view(),               name='employee-update'),
    path('employees/<int:pk>/resign',               EmployeeResignView.as_view(),               name='employee-resign'),
    path('employees/batch-deactivate',              EmployeeBatchDeactivateView.as_view(),      name='employee-batch-deactivate'),
    
    # ── Employee Batch Add ─────────────────────────────────────────
    path('employees/batch-add',                     EmployeeBatchUploadView.as_view(),          name='batch-add-employee'),
    path('employees/batch-add/preview',             EmployeeBatchPreviewView.as_view(),         name='batch-add-preview'),
    path('employees/batch-add/confirm',             EmployeeBatchConfirmView.as_view(),         name='batch-add-confirm'),
    path('employees/batch-add/template',            EmployeeBatchTemplateView.as_view(),        name='batch-add-template'),

    # ── Department ──────────────────────────────────────────────────
    path('departments',                             DepartmentListView.as_view(),               name='department-list'),
    path('departments/create',                      DepartmentCreateView.as_view(),             name='department-create'),
    path('departments/<int:pk>/update',             DepartmentUpdateView.as_view(),             name='department-update'),
    path('departments/<int:pk>/delete',             DepartmentSoftDeleteView.as_view(),         name='department-delete'),
    path('departments/<int:pk>/employees/',         DepartmentEmployeesView.as_view(),          name='department-employees'),

    # ── Positions ──────────────────────────────────────────────────
    path('positions',                               PositionListView.as_view(),                 name='position-list'),
    path('positions/create',                        PositionCreateView.as_view(),               name='position-create'),
    path('positions/<int:pk>/update',               PositionUpdateView.as_view(),               name='position-update'),
    path('positions/<int:pk>/delete',               PositionSoftDeleteView.as_view(),           name='position-delete'),
    path('positions/<int:pk>/employees/',           PositionEmployeesView.as_view(),            name='position-employees'),

    # ── Employee Groups ────────────────────────────────────────────
    path('groups',                                  EmployeeGroupListView.as_view(),            name='group-list'),
    path('groups/create',                           EmployeeGroupCreateView.as_view(),          name='group-create'),
    path('groups/<int:pk>/update',                  EmployeeGroupUpdateView.as_view(),          name='group-update'),
    path('groups/<int:pk>/delete',                  EmployeeGroupSoftDeleteView.as_view(),      name='group-delete'), 
    path('groups/assign/',                          EmployeeGroupAssignView.as_view(),          name='group-assign'),
    path('groups/unassign/',                        EmployeeGroupUnassignView.as_view(),        name='group-unassign'),

    # ── Schedule ───────────────────────────────────────────────────
    path('schedules',                               ScheduleListView.as_view(),                 name='schedule-list'),
    path('schedules/save/',                         ScheduleSaveView.as_view(),                 name='schedule-save'),
    path('schedules/assign/',                       ScheduleAssignRecomputeView.as_view(),      name='schedule-assign'),
    path('recompute-log/',                          RecomputeLogView.as_view(),                 name='recompute-log'),
    path('schedules/unassign/',                     ScheduleUnassignView.as_view(),             name='schedule-unassign'),
    path('schedules/<int:schedule_id>/delete/',     ScheduleSoftDeleteView.as_view(),           name='schedule-delete'),
    path('schedules/<int:schedule_id>/restore/',    ScheduleRestoreView.as_view(),              name='schedule-restore'),
    path('schedules/assign-recompute',              ScheduleAssignRecomputeView.as_view(),      name='schedule-assign-recompute'),
    path('schedules/overrides/',                    ScheduleOverrideView.as_view(),             name='schedule-override'),
    path('schedules/overrides/create/',             ScheduleOverrideCreateView.as_view(),       name='schedule-override-create'),
    path('schedules/overrides/<int:pk>/delete/',    ScheduleOverrideDeleteView.as_view(),       name='schedule-override-delete'),
    path('schedules/absences/',                     AbsenceReportView.as_view(),                name='absence-record'),
    path('unscheduled',                             UnscheduledRecordsView.as_view(),           name='unscheduled-list'),    

    # ── Reports ────────────────────────────────────────────────────
    path('reports/timesheet/',                      TimesheetReportView.as_view(),              name='timesheet-report'),
    path('reports/timesheet/download/',             TimesheetDownloadView.as_view(),            name='timesheet-download'),
    path('reports/timesheet-actual/',               TimesheetActualReportView.as_view(),        name='timesheet-actual-report'),
    path('reports/timesheet-actual/download/',      TimesheetActualDownloadView.as_view(),      name='timesheet-actual-download'),

]