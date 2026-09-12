document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_timesheet';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Credited Clock Hours Report (Total)</strong><br>Generate a full timesheet across a date range. Filter by group or individual employee, then download to Excel.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'daterangepicker',
      attachTo: { element: '#daterangepicker', on: 'right' },
      title: 'Date Range',
      text: 'Click to open the date picker and set a start and end date for the report period.',
    },
    {
      id: 'group-select',
      attachTo: { element: '#EmpGrp-select + .ts-wrapper', on: 'right' },
      title: 'Employee Group',
      text: 'Filter by group. Selecting one narrows the Employee dropdown below to only that group\'s members — in real time, no page reload.',
    },
    {
      id: 'employee-select',
      attachTo: { element: '#timesheet-employee-select + .ts-wrapper', on: 'right' },
      title: 'Employee',
      text: 'Leave on <em>All Employees</em> to generate a full report, or pick one individual. The list is pre-filtered when a group is selected above.',
    },
    {
      id: 'view-btn',
      attachTo: { element: '#view-btn', on: 'right' },
      title: 'View Report',
      text: 'Click to generate. A spinner appears while loading — large date ranges may take a moment.',
    },
    {
      id: 'report-area',
      attachTo: { element: '.col-12.col-lg-9', on: 'left' },
      title: 'Report Area',
      text: 'Each employee gets their own card showing daily clock-in/out pairs, required hours, break, hours worked, overtime, and undertime. Once a report is generated, a <strong>Download Report</strong> button appears at the top right to export the same data to Excel.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('timesheet-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});