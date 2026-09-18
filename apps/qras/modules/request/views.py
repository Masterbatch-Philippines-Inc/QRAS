import json
from datetime import datetime, timezone
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from apps.qras.models.employee import (
    Employee
)
from apps.qras.models.attendance import (
    Attendance,
    AttendanceLog,
    AttendanceStatus,
    LeaveRequest,
    OvertimeRequest,
    UndertimeRequest,
    HalfdayRequest,
)
from apps.qras.modules.auth.decorators import (
    permission_required
)
from apps.qras.modules.auth.helpers import (
    get_dept_queryset_filter,
    get_self_exclude
)
from apps.qras.modules.attendance.helpers import (
    _get_credited_for_undertime,
    format_hours_to_text,
    _compute_halfday_credited,
    compute_leave_days,
    approve_leave,
    reject_leave
)


@method_decorator([permission_required('ot_filing', 'read')], name='dispatch')
class OTLogsView(LoginRequiredMixin, View):

    def get(self, request):
        try:
            employee_id = request.GET.get('employee_id')
            date_str    = request.GET.get('date')
            work_date   = datetime.strptime(date_str, '%Y-%m-%d').date()

            logs = AttendanceLog.objects.filter(
                employee__employee_id=employee_id,
                date=work_date,
                is_replaced=False
            ).order_by('timestamp')

            time_in  = next((timezone.localtime(l.timestamp).strftime('%H:%M') for l in logs if l.is_time_in), None)
            time_out = next((timezone.localtime(l.timestamp).strftime('%H:%M') for l in reversed(list(logs)) if l.is_time_out), None)

            attendance = Attendance.objects.filter(
                employee__employee_id=employee_id,
                date=work_date
            ).select_related('schedule').first()

            return JsonResponse({
                "time_in":         time_in,
                "time_out":        time_out,
                "shift_start":     attendance.schedule.shift_start.strftime('%H:%M') if attendance and attendance.schedule else None,
                "shift_end":       attendance.schedule.shift_end.strftime('%H:%M')   if attendance and attendance.schedule else None,
                "has_record":      attendance is not None,
                "has_existing_ot": OvertimeRequest.objects.filter(attendance=attendance).exists() if attendance else False,
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator([permission_required('approvals_overtime', 'read')], name='dispatch')
class OTDecisionView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='employee__department')
        if dept_filter is None:
            return render(request, 'pages/request/overtimes.django', {'dept_warning': True})

        # Exclude self (Department Head's own linked employee)
        self_exclude = get_self_exclude(request)

        # Employees not OT-exempt
        exempt_employee_pks = list(
            Employee.objects.filter(
                group_memberships__group__ot_filing_exempted=True
            ).values_list('pk', flat=True).distinct()
        )

        # All attendance records with overtime detected, excluding exempt employees
        ot_atts = (
            Attendance.objects
            .filter(att_status__is_overtime=True, **dept_filter)
            .exclude(employee__pk__in=exempt_employee_pks)
            .exclude(employee__pk=self_exclude)
            .select_related('employee', 'employee__position', 'schedule', 'att_status')
            .order_by('-date')
        )

        # Existing OT requests mapped by attendance id
        existing_ot_map = {
            ot.attendance_id: ot
            for ot in OvertimeRequest.objects.select_related('filed_by').filter(
                attendance__in=ot_atts
            )
        }

        # Bulk fetch logs
        att_ids     = [a.id for a in ot_atts]
        emp_dates   = [(a.employee_id, a.date) for a in ot_atts]
        all_logs    = AttendanceLog.objects.filter(
            is_replaced=False
        ).filter(
            employee__attendance__id__in=att_ids
        ).order_by('timestamp')

        from collections import defaultdict
        log_map = defaultdict(list)
        for log in all_logs:
            log_map[(log.employee_id, log.date)].append(log)

        enriched = []
        for att in ot_atts:
            logs     = log_map.get((att.employee_id, att.date), [])
            time_in  = next((timezone.localtime(l.timestamp).strftime('%I:%M %p') for l in logs if l.is_time_in), '—')
            time_out = next((timezone.localtime(l.timestamp).strftime('%I:%M %p') for l in reversed(logs) if l.is_time_out), '—')

            # Raw times for modal pre-fill (HH:MM format)
            raw_time_in  = next((timezone.localtime(l.timestamp).strftime('%H:%M') for l in logs if l.is_time_in), None)
            raw_time_out = next((timezone.localtime(l.timestamp).strftime('%H:%M') for l in reversed(logs) if l.is_time_out), None)

            shift_start = att.schedule.shift_start.strftime('%H:%M') if att.schedule else None
            shift_end   = att.schedule.shift_end.strftime('%H:%M')   if att.schedule else None

            ot = existing_ot_map.get(att.id)
            enriched.append({
                'att':          att,
                'ot':           ot,
                'time_in':      time_in,
                'time_out':     time_out,
                'raw_time_in':  raw_time_in,
                'raw_time_out': raw_time_out,
                'shift_start':  shift_start,
                'shift_end':    shift_end,
                'status':       ot.status if ot else None,
                'has_pre_ot':   bool(raw_time_in and shift_start and raw_time_in < shift_start),
                'has_post_ot':  bool(raw_time_out and shift_end and raw_time_out > shift_end),
            })

        return render(request, 'pages/request/overtimes.django', {'ot_records': enriched})

    def post(self, request):
        try:
            data        = json.loads(request.body)
            att_id      = data.get('att_id')
            decision    = data.get('decision')
            ot_type     = data.get('ot_type')
            ot_hours    = data.get('ot_hours')
            remarks     = data.get('remarks', '')

            if decision not in ('APPROVED', 'REJECTED'):
                return JsonResponse({"error": "Invalid decision."}, status=400)

            att = Attendance.objects.select_related('att_status', 'schedule').get(id=att_id)

            # Derive ot_start and ot_end from type
            logs = AttendanceLog.objects.filter(
                employee=att.employee, date=att.date, is_replaced=False
            ).order_by('timestamp')
            raw_in  = next((timezone.localtime(l.timestamp).time() for l in logs if l.is_time_in), None)
            raw_out = next((timezone.localtime(l.timestamp).time() for l in reversed(list(logs)) if l.is_time_out), None)

            if ot_type == 'pre_shift':
                ot_start = raw_in
                ot_end   = att.schedule.shift_start if att.schedule else raw_in
            else:
                ot_start = att.schedule.shift_end if att.schedule else raw_out
                ot_end   = raw_out

            ot_hours_val = round(float(ot_hours), 2)

            ot, _ = OvertimeRequest.objects.update_or_create(
                attendance=att,
                defaults={
                    'filed_by':   request.user,
                    'ot_type':    ot_type,
                    'ot_start':   ot_start,
                    'ot_end':     ot_end,
                    'ot_hours':   ot_hours_val,
                    'status':     decision,
                    'decided_at': timezone.now(),
                    'remarks':    remarks,
                }
            )

            s = att.att_status
            if decision == 'APPROVED':
                att.overtime_hours = ot_hours_val
                att.save(update_fields=['overtime_hours'])
                s.is_overtime = True
                s.save(update_fields=['is_overtime'])
            else:
                att.overtime_hours = 0
                att.save(update_fields=['overtime_hours'])
                s.is_overtime = False
                s.save(update_fields=['is_overtime'])

            return JsonResponse({
                "status":   "updated",
                "decision": decision,
                "ot_hours": ot_hours_val,
            })

        except Attendance.DoesNotExist:
            return JsonResponse({"error": "Attendance record not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator([permission_required('approvals_undertime', 'read')], name='dispatch')
class UTDecisionView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='attendance__employee__department')
        if dept_filter is None:
            return render(request, 'pages/request/undertimes.django', {'dept_warning': True})

        ut_requests = (
            UndertimeRequest.objects
            .select_related('attendance__employee', 'attendance__schedule', 'attendance__att_status', 'filed_by')
            .filter(status='PENDING', **dept_filter)
            .order_by('-filed_at')
        )
        enriched = []
        for ut in ut_requests:
            att  = ut.attendance
            logs = AttendanceLog.objects.filter(
                employee=att.employee,
                date=att.date,
                is_replaced=False
            ).order_by('timestamp')
            time_in  = next((timezone.localtime(l.timestamp).strftime('%I:%M %p') for l in logs if l.is_time_in), '—')
            time_out = next((timezone.localtime(l.timestamp).strftime('%I:%M %p') for l in reversed(list(logs)) if l.is_time_out), '—')
            enriched.append({"ut": ut, "att": att, "time_in": time_in, "time_out": time_out})

        return render(request, 'pages/request/undertimes.django', {'ut_requests': enriched})

    def post(self, request):
        ut_id    = request.POST.get('ut_id')
        decision = request.POST.get('decision')
        remarks  = request.POST.get('remarks', '')

        if decision not in ('APPROVED', 'REJECTED'):
            return JsonResponse({"error": "Invalid decision."}, status=400)

        try:
            ut            = UndertimeRequest.objects.select_related(
                'attendance__att_status',
                'attendance__schedule'
            ).get(id=ut_id)
            ut.status          = decision
            ut.decided_at      = timezone.now()
            ut.approval_source = 'manual'
            if remarks:
                ut.remarks = remarks
            ut.save()

            att      = ut.attendance
            schedule = att.schedule
            credited = _get_credited_for_undertime(att)

            # is_absent only when: late >= 60mins + PRE-UT + rejected
            late_hours        = float(att.late_hours)
            hours_worked      = float(att.total_work_hours)
            halfday_threshold = float(schedule.halfday_threshold) if schedule else 4.0
            is_disciplinary   = late_hours >= 1.0 and hours_worked < halfday_threshold

            try:
                s = att.att_status
            except AttendanceStatus.DoesNotExist:
                s = AttendanceStatus.objects.create(attendance=att, status='PENDING')

            if decision == 'APPROVED':
                s.is_undertime   = True
                s.is_absent      = False
                s.status         = "APPROVED"
                s.credited_hours = round(credited, 2)
                s.save(update_fields=['is_undertime', 'is_absent', 'status', 'credited_hours'])
            else:
                s.is_undertime   = True
                s.is_absent      = is_disciplinary  # ← only True for late >= 60mins + PRE-UT
                s.status         = "REJECTED"
                s.credited_hours = 0.0 if is_disciplinary else round(credited, 2)
                s.save(update_fields=['is_undertime', 'is_absent', 'status', 'credited_hours'])

            return JsonResponse({"status": "updated", "decision": decision})

        except UndertimeRequest.DoesNotExist:
            return JsonResponse({"error": "UT request not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator([permission_required('approvals_halfday', 'read')], name='dispatch')
class HDDecisionView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='employee__department')
        if dept_filter is None:
            return render(request, 'pages/request/halfdays.django', {'dept_warning': True})

        pending_hd = (
            HalfdayRequest.objects
            .select_related('employee', 'filed_by')
            .filter(status='PENDING', **dept_filter)
            .order_by('-filed_at')
        )
        enriched = []
        for hd in pending_hd:
            attendance = Attendance.objects.filter(
                employee=hd.employee, date=hd.date
            ).select_related('att_status').first()
            logs = AttendanceLog.objects.filter(
                employee=hd.employee, date=hd.date, is_replaced=False
            ).order_by('timestamp')
            time_in  = next((timezone.localtime(l.timestamp).strftime('%I:%M %p') for l in logs if l.is_time_in), '—')
            time_out = next((timezone.localtime(l.timestamp).strftime('%I:%M %p') for l in reversed(list(logs)) if l.is_time_out), '—')
            enriched.append({
                "hd":          hd,
                "attendance":  attendance,
                "time_in":     time_in,
                "time_out":    time_out,
                "total_hours": format_hours_to_text(attendance.total_work_hours) if attendance else '—',
                "late_hours":  format_hours_to_text(attendance.late_hours)       if attendance else '—',
            })

        return render(request, 'pages/request/halfdays.django', {'hd_requests': enriched})

    def post(self, request):
        hd_id    = request.POST.get('hd_id')
        decision = request.POST.get('decision')
        remarks  = request.POST.get('remarks', '')

        if decision not in ('APPROVED', 'REJECTED'):
            return JsonResponse({"error": "Invalid decision."}, status=400)

        try:
            hd            = HalfdayRequest.objects.select_related('employee').get(id=hd_id)
            hd.status     = decision
            hd.decided_at = timezone.now()
            if remarks:
                hd.remarks = remarks
            hd.save()

            attendance = Attendance.objects.filter(
                employee=hd.employee, date=hd.date
            ).select_related('att_status').first()

            if attendance:
                s         = attendance.att_status
                threshold = float(attendance.schedule.halfday_threshold) if attendance.schedule else 4.0
                credited  = _compute_halfday_credited(attendance, threshold, hd.halfday_type)

                if decision == 'APPROVED':
                    s.credited_hours = credited
                    s.status         = "APPROVED"
                    s.save(update_fields=['credited_hours', 'status'])

                elif decision == 'REJECTED':
                    s.credited_hours = credited
                    s.is_absent      = s.is_halfday and not s.is_completed and float(attendance.late_hours) >= 1.0
                    s.status         = "REJECTED"
                    s.save(update_fields=['credited_hours', 'is_absent', 'status'])

            return JsonResponse({"status": "updated", "decision": decision})

        except HalfdayRequest.DoesNotExist:
            return JsonResponse({"error": "Halfday request not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator([permission_required('approvals_leaves', 'read')], name='dispatch')
class LeaveDecisionView(LoginRequiredMixin, View):

    def get(self, request):
        dept_filter = get_dept_queryset_filter(request, dept_field_path='employee__department')
        if dept_filter is None:
            return render(request, 'pages/request/leaves.django', {'dept_warning': True})

        pending_leaves = (
            LeaveRequest.objects
            .select_related('employee', 'filed_by')
            .filter(status='PENDING', **dept_filter)
            .order_by('-filed_at')
        )
        return render(request, 'pages/request/leaves.django', {
            'pending_leaves': pending_leaves,
        })

    def post(self, request):
        leave_id = request.POST.get('leave_id')
        decision = request.POST.get('decision')
        remarks  = request.POST.get('remarks', '')

        if decision not in ('APPROVED', 'REJECTED'):
            return JsonResponse({"error": "Invalid decision."}, status=400)

        try:
            leave = LeaveRequest.objects.select_related('employee').get(id=leave_id)

            if decision == 'APPROVED':
                approve_leave(leave, request.user)
            else:
                reject_leave(leave, remarks, request.user)

            return JsonResponse({"status": "updated", "decision": decision})

        except LeaveRequest.DoesNotExist:
            return JsonResponse({"error": "Leave request not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@method_decorator([permission_required('approvals_leaves', 'read')], name='dispatch')
class LeaveComputeDaysView(LoginRequiredMixin, View):

    def get(self, request):
        try:
            emp_id    = request.GET.get('employee_id')
            date_from = datetime.strptime(request.GET.get('date_from'), '%Y-%m-%d').date()
            date_to   = datetime.strptime(request.GET.get('date_to'),   '%Y-%m-%d').date()
            employee  = Employee.objects.get(employee_id=emp_id)

            num_days, rest_hits = compute_leave_days(date_from, date_to, employee)

            return JsonResponse({
                "num_days":  float(num_days),
                "rest_hits": [d.strftime('%b %d') for d in rest_hits],
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)