document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_ut_approval';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Undertime Approvals</strong><br>Undertime requests are auto-created whenever an employee clocks out before their shift ends. Review each one and approve or reject.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'ut-search',
      attachTo: { element: '#ut-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter the list by employee name or position.',
    },
    {
      id: 'ut-table',
      attachTo: { element: '#ut-table', on: 'top' },
      title: 'UT Requests',
      text: 'Each row shows the employee, date, their time-in/out, the computed undertime hours, any reason on file, and who the record was filed by — typically <em>System</em> since these are auto-generated.',
    },
    {
      id: 'ut-hours-col',
      attachTo: { element: '#ut-table thead tr th:nth-child(5)', on: 'bottom' },
      title: 'UT Hours',
      text: 'The duration the employee left before their shift end. This is deducted from credited hours on rejection. On approval, the employee is not penalised — their credited hours remain as worked.',
    },
    {
      id: 'ut-actions',
      attachTo: { element: '#ut-table thead tr th:last-child', on: 'left' },
      title: 'Actions',
      text: '<strong>Approve</strong> — no deduction; the employee\'s credited hours stay as-is. Use this when the early departure was authorised.<br><strong>Reject</strong> — opens a remarks dialog and the undertime is flagged <em>Under D.A.</em> on the attendance record.',
    },
    {
      id: 'reject-modal-info',
      text: '<strong>Reject Modal</strong><br>Clicking <em>Reject</em> opens a dialog for optional remarks before confirming. The remarks are stored alongside the UT record for disciplinary reference.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('ut-approval-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});