# from datetime import date
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.shortcuts import render
# from django.views import View
# from django.utils import timezone

# from app.employees.models import Employee
# from app.attendance.models import Attendance, AttendanceStatus, OvertimeRequest
# from app.schedules.models import ScheduleActivityLog
# from app.authentication.decorators import permission_required
# from app.authentication.helpers import get_dept_queryset_filter, get_self_exclude
# from django.utils.decorators import method_decorator

# # ─────────────────────────────────────────────────────────────────────────────
# #  DASHBOARD
# # ─────────────────────────────────────────────────────────────────────────────

# @method_decorator([permission_required('dashboard', 'read')], name='dispatch')
# class DashboardView(LoginRequiredMixin, View):

#     def get(self, request):
#         dept_filter = get_dept_queryset_filter(request)
#         if dept_filter is None:
#             return render(request, 'dashboard/dashboard.html', {'dept_warning': True})

#         dept         = getattr(request.user, 'department', None)
#         role         = getattr(request.user, 'role', None)
#         is_dept_head = role and role.name == 'Department Head'
#         today        = date.today()

#         em_filter  = {'department': dept}                        if is_dept_head else {}
#         ml_filter  = {'attendance__employee__department': dept}  if is_dept_head else {}
#         att_filter = {'employee__department': dept}              if is_dept_head else {}
#         sal_filter = {'employee__department': dept}              if is_dept_head else {}

#         exempt_pks = list(
#             Employee.objects
#             .filter(group_memberships__group__ot_filing_exempted=True)
#             .values_list('pk', flat=True)
#             .distinct()
#         )

#         decided_att_ids = set(
#             OvertimeRequest.objects
#             .filter(status__in=['APPROVED', 'REJECTED'])
#             .values_list('attendance_id', flat=True)
#         )

#         self_exclude = get_self_exclude(request)

#         ns_count = Employee.objects.filter(
#             is_active=True, is_resigned=False,
#             attendance__isnull=False, **em_filter
#         ).exclude(schedules__is_active=True).distinct().count()

#         ml_count = AttendanceStatus.objects.filter(
#             has_missing_log=True,
#             attendance__date__lt=today,
#             **ml_filter
#         ).count()

#         ut_count = AttendanceStatus.objects.filter(
#             is_undertime=True,
#             **ml_filter
#         ).count()

#         ot_count = AttendanceStatus.objects.filter(
#             is_overtime=True,
#             **ml_filter
#         ).exclude(
#             attendance__employee__pk__in=exempt_pks
#         ).exclude(
#             attendance__employee__pk=self_exclude
#         ).exclude(
#             attendance__pk__in=decided_att_ids
#         ).count()

#         hd_count = AttendanceStatus.objects.filter(
#             is_halfday=True,
#             **ml_filter
#         ).count()

#         today_count = Attendance.objects.filter(
#             date=today, **att_filter
#         ).count()

#         # ── OT Pending Tiers ──────────────────────────────────
#         # Source of truth is Attendance with is_overtime=True and no decided OTRequest.
#         # Mirrors OTDecisionView logic — OvertimeRequest row only exists after a decision.
#         ot_att_filter = {'employee__department': dept} if is_dept_head else {}
#         now           = timezone.now()

#         exempt_pks = list(
#             Employee.objects
#             .filter(group_memberships__group__ot_filing_exempted=True)
#             .values_list('pk', flat=True)
#             .distinct()
#         )

#         decided_att_ids = set(
#             OvertimeRequest.objects
#             .filter(status__in=['APPROVED', 'REJECTED'])
#             .values_list('attendance_id', flat=True)
#         )

#         self_exclude = get_self_exclude(request)

#         pending_ot_atts = (
#             Attendance.objects
#             .filter(att_status__is_overtime=True, **ot_att_filter)
#             .exclude(employee__pk__in=exempt_pks)
#             .exclude(pk__in=decided_att_ids)
#             .exclude(employee__pk=self_exclude)
#             .select_related('employee', 'att_status')
#             .order_by('date')
#         )

#         tiers = {
#             'overdue': {'label': 'Overdue', 'days': '3+ days', 'color': 'red',    'records': []},
#             'recent':  {'label': 'Recent',  'days': '1–2 days','color': 'yellow', 'records': []},
#             'today':   {'label': 'Today',   'days': 'Today',   'color': 'blue',   'records': []},
#         }

#         for att in pending_ot_atts:
#             age = (now.date() - att.date).days
#             if age >= 3:
#                 tiers['overdue']['records'].append(att)
#             elif age >= 1:
#                 tiers['recent']['records'].append(att)
#             else:
#                 tiers['today']['records'].append(att)

#         def summarize(records):
#             previews = []
#             seen     = set()
#             for r in records:
#                 name = f"{r.employee.last_name}, {r.employee.first_name}"
#                 if name not in seen:
#                     seen.add(name)
#                     previews.append(name)
#                 if len(previews) == 3:
#                     break
#             return {
#                 'count':    len(records),
#                 'previews': previews,
#                 'has_more': len(records) > 3,
#             }

#         ot_pending_tiers = {k: {**v, **summarize(v['records'])} for k, v in tiers.items()}

#         recent_activity = []
#         for sal in ScheduleActivityLog.objects.filter(**sal_filter).select_related(
#             'employee__position', 'assigned_schedule', 'previous_schedule'
#         ).order_by('-acted_at')[:20]:
#             prev = sal.previous_schedule.name if sal.previous_schedule else 'none'
#             recent_activity.append({
#                 'employee': sal.employee,
#                 'activity': f"Assigned to {sal.assigned_schedule.name} (prev: {prev})",
#                 'work_date': None,
#                 'acted_at':  sal.acted_at,
#             })

#         return render(request, 'dashboard/dashboard.html', {
#             'ns_count':          ns_count,
#             'ml_count':          ml_count,
#             'ut_count':          ut_count,
#             'ot_count':          ot_count,
#             'hd_count':          hd_count,
#             'today_count':       today_count,
#             'recent_activity':   recent_activity[:10],
#             'today_display':     timezone.localdate().strftime('%b %d, %Y'),
#             'ot_pending_tiers':  ot_pending_tiers,
#         })