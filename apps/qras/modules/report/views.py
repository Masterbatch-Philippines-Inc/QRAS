from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from datetime import date, timedelta
from django.utils import timezone
from decimal import Decimal
import io
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from apps.qras.models.employee import Employee, EmployeeGroup, EmployeeSchedule, EmployeeRestDay
from apps.qras.models.attendance import AttendanceLog, Attendance
from django.utils.decorators import method_decorator
from apps.qras.modules.auth.decorators import permission_required


BREAK_HOURS    = Decimal('1.0')
REQUIRED_HOURS = Decimal('8.0')


# ═══════════════════════════════════════════════════════════════════
#   HELPERS
# ═══════════════════════════════════════════════════════════════════

def parse_date_range(request):
    """Parse start/end from GET params; default to current Mon–today."""
    today = date.today()
    try:
        start = date.fromisoformat(request.GET.get('start_date', ''))
    except (ValueError, TypeError):
        start = today - timedelta(days=today.weekday())
    try:
        end = date.fromisoformat(request.GET.get('end_date', ''))
    except (ValueError, TypeError):
        end = today
    end = min(end, today)
    return start, end


def get_employees(request):
    """Filter active employees by group and/or individual employee from GET params."""
    group_id    = request.GET.get('group_id', '')
    employee_id = request.GET.get('employee_id', '')
    qs = Employee.objects.filter(is_active=True)
    if group_id:
        qs = qs.filter(group_memberships__group_id=group_id).distinct()
    if employee_id:
        qs = qs.filter(pk=employee_id)
    return qs.order_by('last_name', 'first_name', 'employee_id')


def build_schedule_map(emp_ids):
    """Returns {employee_id: ShiftSchedule} using the most recent active assignment."""
    schedules = (
        EmployeeSchedule.objects
        .filter(employee_id__in=emp_ids, is_active=True)
        .select_related('schedule')
        .order_by('employee_id', '-effective_date')
    )
    result = {}
    for es in schedules:
        if es.employee_id not in result:
            result[es.employee_id] = es.schedule
    return result


def date_is_rest_day(d, emp_id, rest_day_set, schedule_map):
    """
    True if the date is a rest day for this employee.
    Checks personal EmployeeRestDay overrides first, then schedule rest_days
    (which is a JSON list of weekday integers — 0=Monday, 6=Sunday).
    """
    if (emp_id, d) in rest_day_set:
        return True
    sched = schedule_map.get(emp_id)
    if sched and sched.rest_days:
        if d.weekday() in sched.rest_days:
            return True
    return False


def slot_list(logs):
    """
    Sort logs by timestamp and return a flat list of 12 slots:
    [In1, Out1, In2, Out2, ..., In6, Out6]
    Unoccupied slots are None.
    """
    sorted_logs = sorted(logs, key=lambda x: x.timestamp)
    slots = [None] * 12
    for i, log in enumerate(sorted_logs[:12]):
        slots[i] = log
    return slots


def actual_break_and_worked(slots):
    """
    Returns (break_minutes, worked_minutes) from ordered slots.
    Worked = sum of each (Out_n - In_n) pair.
    Break  = sum of gaps between consecutive Out_n → In_(n+1).
    """
    break_m  = 0
    worked_m = 0
    for i in range(0, 12, 2):
        tin  = slots[i]
        tout = slots[i + 1] if i + 1 < 12 else None
        if tin and tout:
            worked_m += int((tout.timestamp - tin.timestamp).total_seconds() // 60)
        next_tin = slots[i + 2] if i + 2 < 12 else None
        if tout and next_tin:
            break_m += int((next_tin.timestamp - tout.timestamp).total_seconds() // 60)
    return break_m, worked_m


def fmt_hm(minutes):
    """Format integer minutes as '9 Hrs and 55 Mins'."""
    h, m = divmod(abs(int(minutes)), 60)
    return f"{h} Hrs and {m} Mins"


def fmt_time(dt):
    """Format a datetime as '7:18 am' style, converted to local timezone."""
    local_dt = timezone.localtime(dt)
    return local_dt.strftime('%I:%M %p').lstrip('0').lower()

# ═══════════════════════════════════════════════════════════════════
#   REPORT DATA BUILDERS
# ═══════════════════════════════════════════════════════════════════

def assemble_timesheet(employees, start_date, end_date):
    """
    Returns a list of per-employee dicts for the standard Timesheet report.
    Hours Required: hardcoded 8.
    Break:  fixed 1 hr if employee has ≥2 logs that day.
    Worked: Attendance.total_work_hours.
    OT/UT:  Attendance.overtime_hours / undertime_hours.
    """
    emp_ids   = list(employees.values_list('pk', flat=True))
    date_list = [start_date + timedelta(days=i)
                 for i in range((end_date - start_date).days + 1)]

    # Bulk-fetch to avoid N+1 queries
    logs_qs = (
        AttendanceLog.objects
        .filter(employee_id__in=emp_ids,
                date__range=(start_date, end_date),
                is_replaced=False)
        .order_by('timestamp')
    )
    att_qs = Attendance.objects.filter(
        employee_id__in=emp_ids,
        date__range=(start_date, end_date)
    ).select_related('att_status')
    rd_qs = EmployeeRestDay.objects.filter(
        employee_id__in=emp_ids,
        date__range=(start_date, end_date)
    )

    logs_map = {}
    for log in logs_qs:
        logs_map.setdefault((log.employee_id, log.date), []).append(log)

    att_map  = {(a.employee_id, a.date): a for a in att_qs}
    rest_set = {(rd.employee_id, rd.date) for rd in rd_qs}
    sched_map = build_schedule_map(emp_ids)

    report = []
    for emp in employees:
        rows = []
        days_present = 0
        days_absent  = 0
        tot = {k: Decimal(0) for k in
               ('hrs_required', 'hrs_break', 'hrs_worked', 'hrs_ot', 'hrs_ut')}

        for d in date_list:
            if date_is_rest_day(d, emp.pk, rest_set, sched_map):
                continue

            logs = logs_map.get((emp.pk, d), [])
            if not logs:
                days_absent += 1
                continue

            days_present += 1
            att  = att_map.get((emp.pk, d))
            slts = slot_list(logs)

            hrs_req    = REQUIRED_HOURS
            hrs_break  = BREAK_HOURS if len(logs) >= 2 else Decimal(0)
            hrs_worked = att.att_status.credited_hours if att and hasattr(att, 'att_status') else Decimal(0)
            hrs_ot     = att.overtime_hours   if att else Decimal(0)
            hrs_ut     = att.undertime_hours  if att else Decimal(0)

            tot['hrs_required'] += hrs_req
            tot['hrs_break']    += hrs_break
            tot['hrs_worked']   += hrs_worked
            tot['hrs_ot']       += hrs_ot
            tot['hrs_ut']       += hrs_ut

            rows.append({
                'date':         d,
                'slots':        slts,
                'slots_fmt':    [fmt_time(s.timestamp) if s else '' for s in slts],
                'hrs_required': hrs_req,
                'hrs_break':    hrs_break,
                'hrs_worked':   hrs_worked,
                'hrs_ot':       hrs_ot,
                'hrs_ut':       hrs_ut,
            })

        report.append({
            'employee':     emp,
            'rows':         rows,
            'totals':       tot,
            'days_present': days_present,
            'days_absent':  days_absent,
        })
    return report


def assemble_timesheet_actual(employees, start_date, end_date):
    """
    Returns per-employee dicts for the Timesheet (Actual Break & Hours) report.
    Break and worked hours are derived from raw log timestamps, not Attendance model.
    """
    emp_ids   = list(employees.values_list('pk', flat=True))
    date_list = [start_date + timedelta(days=i)
                 for i in range((end_date - start_date).days + 1)]

    logs_qs = (
        AttendanceLog.objects
        .filter(employee_id__in=emp_ids,
                date__range=(start_date, end_date),
                is_replaced=False)
        .order_by('timestamp')
    )
    rd_qs = EmployeeRestDay.objects.filter(
        employee_id__in=emp_ids,
        date__range=(start_date, end_date)
    )

    logs_map = {}
    for log in logs_qs:
        logs_map.setdefault((log.employee_id, log.date), []).append(log)

    rest_set  = {(rd.employee_id, rd.date) for rd in rd_qs}
    sched_map = build_schedule_map(emp_ids)

    report = []
    for emp in employees:
        rows = []
        days_present   = 0
        days_absent    = 0
        total_break_m  = 0
        total_worked_m = 0

        for d in date_list:
            if date_is_rest_day(d, emp.pk, rest_set, sched_map):
                continue

            logs = logs_map.get((emp.pk, d), [])
            if not logs:
                days_absent += 1
                continue

            days_present += 1
            slts            = slot_list(logs)
            break_m, wrk_m  = actual_break_and_worked(slts)
            total_break_m  += break_m
            total_worked_m += wrk_m

            rows.append({
                'date':        d,
                'slots':       slts,
                'slots_fmt':   [fmt_time(s.timestamp) if s else '' for s in slts],
                'break_m':     break_m,
                'worked_m':    wrk_m,
                'break_disp':  fmt_hm(break_m),
                'worked_disp': fmt_hm(wrk_m),
            })

        report.append({
            'employee':          emp,
            'rows':              rows,
            'total_break_m':     total_break_m,
            'total_worked_m':    total_worked_m,
            'total_break_disp':  fmt_hm(total_break_m),
            'total_worked_disp': fmt_hm(total_worked_m),
            'days_present':      days_present,
            'days_absent':       days_absent,
        })
    return report


# ═══════════════════════════════════════════════════════════════════
#   EXCEL BUILDERS
# ═══════════════════════════════════════════════════════════════════

_THIN = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'),  bottom=Side(style='thin'),
)
_CENTER = Alignment(horizontal='center', vertical='center')
_RIGHT  = Alignment(horizontal='right',  vertical='center')
_LEFT   = Alignment(horizontal='left',   vertical='center')

_HEADER_FILL = PatternFill('solid', fgColor='D9D9D9')
_EMP_FILL    = PatternFill('solid', fgColor='BDD7EE')   # light blue
_TOTAL_FILL  = PatternFill('solid', fgColor='EDEDED')


def _cell(ws, row, col, value='', bold=False, fill=None, align=None, border=True, font_size=9):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(bold=bold, size=font_size)
    if fill:
        c.fill = fill
    if align:
        c.alignment = align
    if border:
        c.border = _THIN
    return c


def build_timesheet_excel(report_data, start_date, end_date):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Timesheet"

    # ── Title block ──────────────────────────────────────
    ws.merge_cells('A1:R1')
    c = ws['A1']
    c.value     = 'TIMESHEET REPORT'
    c.font      = Font(bold=True, size=13)
    c.alignment = _CENTER

    ws.merge_cells('A2:R2')
    c = ws['A2']
    c.value     = f'From {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}'
    c.font      = Font(size=10)
    c.alignment = _CENTER

    row = 4  # blank row 3

    HEADERS = ['Date','In 1','Out 1','In 2','Out 2','In 3','Out 3',
               'In 4','Out 4','In 5','Out 5','In 6','Out 6',
               'Hrs Required','Tot Hrs Break','Hrs Worked','Hrs OT','Hrs UT']
    COL_W   = [12,9,9,9,9,9,9,9,9,9,9,9,9,13,13,11,9,9]

    for emp_data in report_data:
        emp = emp_data['employee']
        mid = emp.middle_name[0] + '.' if emp.middle_name else ''
        name = f"{emp.last_name.upper()}, {emp.first_name.upper()} {mid}".strip()

        # Employee header row
        ws.merge_cells(f'A{row}:R{row}')
        c = ws[f'A{row}']
        c.value     = f'Employee: {name} ({emp.employee_id})'
        c.font      = Font(bold=True, size=10)
        c.fill      = _EMP_FILL
        c.alignment = _LEFT
        c.border    = _THIN
        ws.row_dimensions[row].height = 16
        row += 1

        # Column header row
        for col, h in enumerate(HEADERS, 1):
            _cell(ws, row, col, h, bold=True, fill=_HEADER_FILL, align=_CENTER)
        ws.row_dimensions[row].height = 14
        row += 1

        # Data rows
        for r in emp_data['rows']:
            _cell(ws, row, 1, r['date'].strftime('%m/%d/%Y'), align=_CENTER)
            for i, t in enumerate(r['slots_fmt']):
                _cell(ws, row, i + 2, t, align=_CENTER)
            for col, key in zip(range(14, 19),
                                ['hrs_required','hrs_break','hrs_worked','hrs_ot','hrs_ut']):
                _cell(ws, row, col, float(r[key]), align=_RIGHT)
            row += 1

        # Total row
        ws.merge_cells(f'A{row}:M{row}')
        c = ws[f'A{row}']
        c.value     = 'Total:'
        c.font      = Font(bold=True, size=9)
        c.fill      = _TOTAL_FILL
        c.alignment = _LEFT
        c.border    = _THIN
        for col, key in zip(range(14, 19),
                            ['hrs_required','hrs_break','hrs_worked','hrs_ot','hrs_ut']):
            _cell(ws, row, col, float(emp_data['totals'][key]),
                  bold=True, fill=_TOTAL_FILL, align=_RIGHT)
        row += 1

        # Days present / absent
        ws.merge_cells(f'A{row}:R{row}')
        c = ws[f'A{row}']
        c.value     = (f"Days Present  {emp_data['days_present']}"
                       f"          Days Absent  {emp_data['days_absent']}")
        c.font      = Font(size=9)
        c.alignment = _LEFT
        c.border    = _THIN
        row += 2  # blank line between employees

    # Column widths
    for i, w in enumerate(COL_W, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = 'B1'
    return wb


def build_timesheet_actual_excel(report_data, start_date, end_date):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Timesheet Actual"

    ws.merge_cells('A1:O1')
    c = ws['A1']
    c.value     = 'TIMESHEET REPORT (Actual Break and Hours Worked)'
    c.font      = Font(bold=True, size=13)
    c.alignment = _CENTER

    ws.merge_cells('A2:O2')
    c = ws['A2']
    c.value     = f'From {start_date.strftime("%B %d, %Y")} to {end_date.strftime("%B %d, %Y")}'
    c.font      = Font(size=10)
    c.alignment = _CENTER

    row = 4

    HEADERS = ['Date','In 1','Out 1','In 2','Out 2','In 3','Out 3',
               'In 4','Out 4','In 5','Out 5','In 6','Out 6',
               'Tot Hrs Break','Hrs Worked']
    COL_W   = [12,9,9,9,9,9,9,9,9,9,9,9,9,22,22]

    for emp_data in report_data:
        emp = emp_data['employee']
        mid  = emp.middle_name[0] + '.' if emp.middle_name else ''
        name = f"{emp.last_name}, {emp.first_name} {mid}".strip()

        ws.merge_cells(f'A{row}:O{row}')
        c = ws[f'A{row}']
        c.value     = f'Employee: {name} ({emp.employee_id})'
        c.font      = Font(bold=True, size=10)
        c.fill      = _EMP_FILL
        c.alignment = _LEFT
        c.border    = _THIN
        ws.row_dimensions[row].height = 16
        row += 1

        for col, h in enumerate(HEADERS, 1):
            _cell(ws, row, col, h, bold=True, fill=_HEADER_FILL, align=_CENTER)
        ws.row_dimensions[row].height = 14
        row += 1

        for r in emp_data['rows']:
            _cell(ws, row, 1, r['date'].strftime('%m/%d/%Y'), align=_CENTER)
            for i, t in enumerate(r['slots_fmt']):
                _cell(ws, row, i + 2, t, align=_CENTER)
            _cell(ws, row, 14, r['break_disp'],  align=_CENTER)
            _cell(ws, row, 15, r['worked_disp'], align=_CENTER)
            row += 1

        ws.merge_cells(f'A{row}:M{row}')
        c = ws[f'A{row}']
        c.value     = 'Total:'
        c.font      = Font(bold=True, size=9)
        c.fill      = _TOTAL_FILL
        c.alignment = _LEFT
        c.border    = _THIN
        _cell(ws, row, 14, emp_data['total_break_disp'],  bold=True, fill=_TOTAL_FILL, align=_CENTER)
        _cell(ws, row, 15, emp_data['total_worked_disp'], bold=True, fill=_TOTAL_FILL, align=_CENTER)
        row += 1

        ws.merge_cells(f'A{row}:O{row}')
        c = ws[f'A{row}']
        c.value     = (f"Days Present  {emp_data['days_present']}"
                       f"          Days Absent  {emp_data['days_absent']}")
        c.font      = Font(size=9)
        c.alignment = _LEFT
        c.border    = _THIN
        row += 2

    for i, w in enumerate(COL_W, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = 'B1'
    return wb


# ═══════════════════════════════════════════════════════════════════
#   VIEWS
# ═══════════════════════════════════════════════════════════════════

class _ReportBaseView(LoginRequiredMixin, TemplateView):
    """Shared context setup for both report types."""

    def get_context_data(self, **kwargs):
        ctx        = super().get_context_data(**kwargs)
        start, end = parse_date_range(self.request)

        ctx['groups']        = EmployeeGroup.objects.filter(is_active=True).order_by('group_name')
        ctx['employees_list'] = (Employee.objects
                                 .filter(is_active=True)
                                 .order_by('last_name', 'first_name'))
        ctx['start_date']    = start.isoformat()
        ctx['end_date']      = end.isoformat()
        ctx['group_id']      = self.request.GET.get('group_id', '')
        ctx['employee_id']   = self.request.GET.get('employee_id', '')
        ctx['report_ready']  = False

        if self.request.GET.get('view') == '1':
            employees = get_employees(self.request)
            ctx.update(self._build_report(employees, start, end))
            ctx['report_ready']  = True
            ctx['report_start']  = start
            ctx['report_end']    = end

        return ctx

    def _build_report(self, employees, start, end):
        raise NotImplementedError


@method_decorator([permission_required('reports_timesheet_total', 'read')], name='dispatch')
class TimesheetReportView(_ReportBaseView):
    template_name = 'pages/report/credited.django'

    def _build_report(self, employees, start, end):
        return {'report_data': assemble_timesheet(employees, start, end)}


@method_decorator([permission_required('reports_timesheet_actual', 'read')], name='dispatch')
class TimesheetActualReportView(_ReportBaseView):
    template_name = 'pages/report/actuals.django'

    def _build_report(self, employees, start, end):
        return {'report_data': assemble_timesheet_actual(employees, start, end)}


@method_decorator([permission_required('reports_timesheet_total', 'read')], name='dispatch')
class TimesheetDownloadView(LoginRequiredMixin, View):
    def get(self, request):
        start, end = parse_date_range(request)
        employees  = get_employees(request)
        data = assemble_timesheet(employees, start, end)
        wb   = build_timesheet_excel(data, start, end)
        buf  = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = (
            f'attachment; filename="timesheet_{start}_{end}.xlsx"'
        )
        return resp


@method_decorator([permission_required('reports_timesheet_actual', 'read')], name='dispatch')
class TimesheetActualDownloadView(LoginRequiredMixin, View):
    def get(self, request):
        start, end = parse_date_range(request)
        employees  = get_employees(request)
        data = assemble_timesheet_actual(employees, start, end)
        wb   = build_timesheet_actual_excel(data, start, end)
        buf  = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = (
            f'attachment; filename="timesheet_actual_{start}_{end}.xlsx"'
        )
        return resp

