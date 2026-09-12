document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_timesheet_actual';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Timesheet Report (Actual)</strong><br>Same layout as the Total report — but break duration and hours worked come from <em>raw log timestamps</em> instead of the fixed-deduction model.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'daterangepicker',
      attachTo: { element: '#daterangepicker', on: 'right' },
      title: 'Date Range',
      text: 'Click to open the date picker and set the report period.',
    },
    {
      id: 'group-select',
      attachTo: { element: '#t-actual-group-select + .ts-wrapper', on: 'right' },
      title: 'Employee Group',
      text: 'Filter by group. The Employee dropdown updates instantly when a group is selected.',
    },
    {
      id: 'employee-select',
      attachTo: { element: '#t-actual-employee-select + .ts-wrapper', on: 'right' },
      title: 'Employee',
      text: 'Leave on <em>All Employees</em> for a full report, or narrow to one person.',
    },
    {
      id: 'actual-info',
      attachTo: { element: '.alert-info', on: 'top' },
      title: 'What Makes This Report Different',
      text: 'Break time here is the literal gap between an out-punch and the next in-punch. The Total report uses a fixed break deduction instead. Use this version when you need to audit actual on-site hours.',
    },
    {
      id: 'view-btn',
      attachTo: { element: '#view-btn', on: 'right' },
      title: 'View Report',
      text: 'Click to generate. A <strong>Download Report</strong> button appears at the top right once results load.',
    },
    {
      id: 'report-area',
      attachTo: { element: '.col-12.col-lg-9', on: 'left' },
      title: 'Report Area',
      text: 'Each employee card shows all clock-in/out pairs for the period, with actual break totals and hours worked in the final two columns.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('timesheet-actual-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});