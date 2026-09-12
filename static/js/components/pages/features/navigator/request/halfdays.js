document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_hd_approval';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Halfday Approvals</strong><br>Halfday requests are auto-detected when an employee works roughly half their shift or arrives 60+ minutes late before the dedicated lunch cutoff. Review each one and approve or reject.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'hd-search',
      attachTo: { element: '#hd-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter the list by employee name or position.',
    },
    {
      id: 'hd-table',
      attachTo: { element: '#hd-table', on: 'top' },
      title: 'Halfday Requests',
      text: 'Each row shows the employee, date, halfday type (<strong>AM</strong> or <strong>PM</strong>), their time in/out, total hours worked, late hours, and any reason on file.',
    },
    {
      id: 'hd-type-col',
      attachTo: { element: '#hd-table thead tr th:nth-child(3)', on: 'bottom' },
      title: 'AM vs PM',
      text: '<strong>AM</strong> — the employee was absent or late for the morning half of their shift.<br><strong>PM</strong> — the employee left before completing the afternoon half.',
    },
    {
      id: 'hd-actions',
      attachTo: { element: '#hd-table thead tr th:last-child', on: 'left' },
      title: 'Actions',
      text: '<strong>Approve</strong> — credited hours are computed and saved; the record is marked complete.<br><strong>Reject</strong> — opens a remarks form. The credited hours are still saved but the record is flagged <em>Under D.A.</em> to indicate disciplinary action.',
    },
    {
      id: 'reject-modal-info',
      text: '<strong>Reject Modal</strong><br>When you click <em>Reject</em>, a small dialog appears asking for optional remarks. Enter the reason for rejection then click <strong>Confirm Reject</strong>. The remarks are stored alongside the record for audit purposes.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('hd-approval-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});