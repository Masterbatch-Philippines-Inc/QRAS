document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_unscheduled';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Unscheduled Employees</strong><br>This page lists employees who have attendance logs but no active shift schedule — their hours cannot be computed until a schedule is assigned.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'ns-search',
      attachTo: { element: '#ns-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter this list by employee name, department, or position.',
    },
    {
      id: 'ns-table',
      attachTo: { element: '#ns-table', on: 'top' },
      title: 'Unscheduled List',
      text: 'Each row shows an employee flagged <strong>UN</strong> (unscheduled) alongside how many attendance records they already have. Those records stay at zero credited hours until a schedule is applied.',
    },
    {
      id: 'schedule-select',
      attachTo: { element: '.schedule-select', on: 'bottom' },
      title: 'Pick a Schedule',
      text: 'Choose the shift to apply to this employee from the dropdown. Each row has its own selector.',
    },
    {
      id: 'btn-scope',
      attachTo: { element: '.btn-scope', on: 'bottom' },
      title: 'Recompute Scope',
      text: 'Choose <strong>All</strong> to recompute every existing record under the new schedule, or <strong>Today</strong> to only affect today\'s entry and leave past records untouched. This choice is required before assigning.',
    },
    {
      id: 'btn-assign-ns',
      attachTo: { element: '.btn-assign-ns', on: 'left' },
      title: 'Assign & Recompute',
      text: 'Click <strong>Assign</strong> to apply the schedule. Unlike the main Schedules page, this triggers an immediate <em>recomputation</em> of all existing logs for that employee. A warning appears if any logs fall outside the new shift window.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('unscheduled-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});