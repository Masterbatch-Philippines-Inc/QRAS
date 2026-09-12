document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_leave_approval';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Leave Approvals</strong><br>Leave requests are filed on behalf of employees by admin or department heads. Review each one and approve or reject.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'leave-search',
      attachTo: { element: '#leave-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter the list by employee name or position.',
    },
    {
      id: 'leave-table',
      attachTo: { element: '#leave-table', on: 'top' },
      title: 'Leave Requests',
      text: 'Each row shows the employee, LF number, leave type, date range, number of days, reason, and who filed the request.',
    },
    {
      id: 'leave-type-col',
      attachTo: { element: '#leave-table thead tr th:nth-child(3)', on: 'bottom' },
      title: 'Leave Types',
      text: '<strong>Sick / Vacation</strong> — on approval, an excusal record is created so the employee appears as <em>Excused</em> instead of Absent for those dates.<br><strong>Undertime Leave</strong> — on approval, the matching undertime request for the same date is automatically approved as well.',
    },
    {
      id: 'leave-filed-by',
      attachTo: { element: '#leave-table thead tr th:nth-child(8)', on: 'left' },
      title: 'Filed By',
      text: 'Shows which system user filed the request and when. Useful for tracking who initiated the leave on the employee\'s behalf.',
    },
    {
      id: 'leave-actions',
      attachTo: { element: '#leave-table thead tr th:last-child', on: 'left' },
      title: 'Actions',
      text: '<strong>Approve</strong> — confirms the leave and triggers any downstream effects (excusal or UT auto-approval).<br><strong>Reject</strong> — opens a remarks dialog. The request is closed without creating any excusal or UT approval.',
    },
    {
      id: 'reject-modal-info',
      text: '<strong>Reject Modal</strong><br>Clicking <em>Reject</em> opens a small dialog for optional remarks. Enter the reason and click <strong>Confirm Reject</strong> to finalise. Remarks are stored on the leave record.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('leave-approval-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});