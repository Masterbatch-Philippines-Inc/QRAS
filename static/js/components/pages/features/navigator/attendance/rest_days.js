document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_rest_days';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Rest Day Management</strong><br>Assign specific rest day dates per employee. These override the schedule\'s default rest day — useful for guards and rotational staff.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'emp-select',
      attachTo: { element: '#emp-select', on: 'bottom' },
      title: 'Select Employee',
      text: 'Choose an employee. Their existing personal rest day assignments will load immediately in the table on the right.',
    },
    {
      id: 'rest-date',
      attachTo: { element: '#rest-date', on: 'bottom' },
      title: 'Rest Day Date',
      text: 'Pick the date to mark as a rest day for this employee. This date will be excluded from absence detection and attendance computation.',
    },
    {
      id: 'btn-assign',
      attachTo: { element: '#btn-assign', on: 'bottom' },
      title: 'Assign Rest Day',
      text: 'Saves the override. It takes effect immediately — past attendance records that reference this date may be affected on next recomputation.',
    },
    {
      id: 'rest-days-list',
      attachTo: { element: '#rest-days-right-card', on: 'top' },
      title: 'Assigned Rest Days',
      text: 'Lists all personal rest day overrides for the selected employee. Click <strong>Remove</strong> on any row to delete it.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('rest-days-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));
});