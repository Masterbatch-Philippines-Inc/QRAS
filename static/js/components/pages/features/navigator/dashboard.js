 document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_dashboard';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Welcome to the Dashboard!</strong><br>This quick tour walks you through everything on this page.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'card-undertime',
      attachTo: { element: '#card-undertime', on: 'bottom' },
      title: 'Undertime',
      text: 'Total attendance records flagged as undertime — where an employee clocked out before their shift ended. Click <strong>Review</strong> to filter the attendance page to undertime logs.',
    },
    {
      id: 'card-overtime',
      attachTo: { element: '#card-overtime', on: 'bottom' },
      title: 'Overtime',
      text: 'Total attendance records where an employee worked past their shift end regularly without the needs of approval. Click <strong>Review</strong> to filter the attendance page to overtime logs.',
    },
    {
      id: 'card-halfday',
      attachTo: { element: '#card-halfday', on: 'bottom' },
      title: 'Half-day',
      text: 'Total attendance records flagged as half-day — either by working roughly half the shift or arriving late by 60 minutes or above. Click <strong>Review</strong> to filter the attendance page to half-day logs.',
    },
    {
      id: 'card-unscheduled',
      attachTo: { element: '#card-unscheduled', on: 'bottom' },
      title: 'Unscheduled Employees',
      text: 'Employees who have attendance logs but no active shift schedule. Assign them a schedule so hours can be computed correctly.',
    },
    {
      id: 'card-ml',
      attachTo: { element: '#card-ml', on: 'bottom' },
      title: 'Missing Logs',
      text: 'Past attendance records where only a time-in or time-out was logged. Click <strong>Review</strong> to go to the attendance page and correct them.',
    },
    {
      id: 'card-today',
      attachTo: { element: '#card-today', on: 'bottom' },
      title: "Today's Logs",
      text: "A count of employees with an attendance record for today. Use this as a quick pulse check on who's clocked in.",
    },
    {
      id: 'recent-decisions',
      attachTo: { element: '#card-recent-decisions', on: 'top' },
      title: 'Recent Schedule Activity',
      text: 'A log of the latest schedule assignments. Each row shows which employee was assigned, what schedule they moved to, and when the change was made.',
    },
    {
      id: 'card-ot-pending',
      attachTo: { element: '#card-ot-pending', on: 'top' },
      title: 'Overtime Pending Approval',
      text: 'Pending overtime records grouped by how long they have been waiting. <strong>Overdue</strong> means 3 or more days, <strong>Recent</strong> means 1 to 2 days, and <strong>Today</strong> means filed today. Each row shows how many records are waiting and a preview of which employees are involved. Click <strong>View All</strong> to go to the overtime approval page.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('dashboard-btn-help-tour')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));
});