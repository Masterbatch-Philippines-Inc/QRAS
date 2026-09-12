document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_settings_positions';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Dept. Positions</strong><br>Manage job titles linked to each department. Positions are assigned to employees and appear on attendance and timesheet reports.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'search',
      attachTo: { element: '#dept-pos-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter positions by title or department name.',
    },
    {
      id: 'dept-filter',
      attachTo: { element: 'select[name="department"]', on: 'bottom' },
      title: 'Department Filter',
      text: 'Narrow the list to a single department. Useful when a department has many positions.',
    },
    {
      id: 'inactive-toggle',
      attachTo: { element: 'input[name="show_inactive"]', on: 'bottom' },
      title: 'Show Inactive',
      text: 'Toggle to include deactivated positions. Inactive positions are hidden from employee assignment dropdowns.',
    },
    {
      id: 'add-pos-btn',
      attachTo: { element: '[data-bs-target="#modalCreatePos"]', on: 'bottom' },
      title: 'Add New Position',
      text: 'Opens a form to create a position. You\'ll enter the job title and link it to a department.',
    },
    {
      id: 'table',
      attachTo: { element: '#tours-pos-rec', on: 'bottom' },
      title: 'Position Records',
      text: 'Lists all positions with their linked department and employee count. Click the employee count to see who holds that position.',
    },
    {
      id: 'actions',
      title: 'Actions',
      text: '<strong>Edit</strong> — change the title or reassign the position to a different department.<br><strong>Deactivate / Restore</strong> — soft-deletes the position, removing it from assignment dropdowns.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('tours-pos-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));

  // ── Modal tours (wire up when modal HTML files are available) ──────────────

  function createPosModalTour() {
    return createTour([
      {
        id: 'create-title',
        attachTo: { element: '#createTitle', on: 'bottom' },
        title: 'Position Title',
        text: 'The job title for this position (e.g. Warehouse Supervisor).',
      },
      {
        id: 'create-dept',
        attachTo: { element: '#createDeptId', on: 'bottom' },
        title: 'Department',
        text: 'Link this position to a department. Only one department per position.',
      },
      {
        id: 'create-save',
        attachTo: { element: '#btnCreatePos', on: 'top' },
        title: 'Save',
        text: 'Creates the position and makes it available in employee assignment forms.',
      },
    ]);
  }

  function editPosModalTour() {
    return createTour([
      {
        id: 'edit-title',
        attachTo: { element: '#editTitle', on: 'bottom' },
        title: 'Position Title',
        text: 'Update the job title. The change reflects on all employees currently assigned this position.',
      },
      {
        id: 'edit-dept',
        attachTo: { element: '#editPostDeptId', on: 'bottom' },
        title: 'Department',
        text: 'Reassign the position to a different department if needed.',
      },
      {
        id: 'edit-save',
        attachTo: { element: '#btnEditPos', on: 'top' },
        title: 'Save Changes',
        text: 'Applies your edits. Existing employee assignments are not affected — only the display name and department link update.',
      },
    ]);
  }
});