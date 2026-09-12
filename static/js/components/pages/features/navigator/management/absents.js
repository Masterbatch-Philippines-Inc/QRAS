document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_absences';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Absence Records</strong><br>This page shows which employees did not clock in for a chosen date range, and whether they were excused by an approved leave.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'employee-filter',
      attachTo: { element: '#abs-emp-select + .ts-wrapper', on: 'bottom' },
      title: 'Filter by Employee',
      text: 'Optionally narrow results to a single employee. Leave this as <strong>All employees</strong> to see absences across your entire department.',
    },
    {
      id: 'date-range',
      attachTo: { element: '#abs-daterangepicker', on: 'bottom' },
      title: 'Select a Date Range',
      text: 'Pick a start and end date. If you submit without selecting a range, the system defaults to the current month. Employees on rest days are automatically excluded from results.',
    },
    {
      id: 'absence-table',
      attachTo: { element: '#absence-table', on: 'top' },
      title: 'Absence List',
      text: 'Each row is an employee with no attendance log for that date. The table shows their department, position, and assigned schedule so you have full context.',
    },
    {
      id: 'status-col',
      attachTo: { element: '#absence-table thead tr th:last-child', on: 'left' },
      title: 'Status Column',
      text: '<strong>Absent</strong> — no log and no approved leave on file.<br><strong>Excused</strong> — the employee has an approved leave covering that date, with the leave type shown.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('absences-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});