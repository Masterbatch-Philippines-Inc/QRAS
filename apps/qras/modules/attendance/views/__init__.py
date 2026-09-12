from .attendance import (
    AttendanceRecordView,
    EmployeeAttendanceLogsView,
    ManualAttendanceView,
    EmployeeRestDayView,
    RestDayManagementView,
    MissingLogView,
    ManualOverwriteAttendanceView,
)
from .approvals import (
    ApprovalRecordView,
)
from .dashboard import (
    DashboardView
)
from .requests import (
    OTFilingView,
    OTLogsView,
    OTDecisionView,
    UTDecisionView,
    HDDecisionView,
    LeaveFilingView, 
    LeaveDecisionView,
    LeaveComputeDaysView
)

from app.attendance.views.scan_upload import (
    ScanUploadView,
    ScanUploadParseView,
    ScanUploadSaveView,
)

from app.attendance.views.live_updates import AttendanceLiveUpdateView