document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_settings_departments';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Departments</strong><br>Manage the departments in your organization. Departments are used to scope employees, approvals, and reports.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'search',
      attachTo: { element: '#dept-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter departments by name or code as you type.',
    },
    {
      id: 'inactive-toggle',
      attachTo: { element: 'form .form-switch', on: 'bottom' },
      title: 'Show Inactive',
      text: 'Toggle this switch to include deactivated departments in the list. Inactive departments are hidden by default.',
    },
    {
      id: 'new-dept-btn',
      attachTo: { element: '[data-bs-target="#modalCreateDept"]', on: 'bottom' },
      title: 'New Department',
      text: 'Opens a form to create a new department. You will provide a name and a short code (e.g. HR, IT, OPS).',
    },
    {
      id: 'table',
      attachTo: { element: '#tour-dept-rec', on: 'bottom' },
      title: 'Department Records',
      text: 'Lists all departments with their code and current employee count. Click the employee count to view which employees belong to that department.',
    },
    {
      id: 'actions',
      attachTo: { element: '#tours-dept-rec-actions', on: 'left' },
      title: 'Actions',
      text: '<strong>Edit</strong> — update the department name or code.<br><strong>Deactivate / Restore</strong> — soft-deletes the department. Deactivated departments are hidden from selection dropdowns across the system.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('tours-dept-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));

  // ── Modal tours (wire up when modal HTML files are available) ──────────────

  function createDeptModalTour() {
    return createTour([
      {
        id: 'create-name',
        attachTo: { element: '#createName', on: 'bottom' },
        title: 'Department Name',
        text: 'Enter the full name of the department (e.g. Human Resources).',
      },
      {
        id: 'create-code',
        attachTo: { element: '#createCode', on: 'bottom' },
        title: 'Department Code',
        text: 'A short uppercase identifier used in badges and reports (e.g. HR, IT, OPS). Must be unique.',
      },
      {
        id: 'create-save',
        attachTo: { element: '#btnCreateDept', on: 'top' },
        title: 'Save',
        text: 'Saves the new department. It becomes immediately available across the system.',
      },
    ]);
  }

  function editDeptModalTour() {
    return createTour([
      {
        id: 'edit-name',
        attachTo: { element: '#editName', on: 'bottom' },
        title: 'Department Name',
        text: 'Update the department\'s display name. Changes reflect everywhere the department is shown.',
      },
      {
        id: 'edit-code',
        attachTo: { element: '#editCode', on: 'bottom' },
        title: 'Department Code',
        text: 'Update the short code. Be careful — codes appear in existing reports and exports.',
      },
      {
        id: 'edit-save',
        attachTo: { element: '#btnEditDept', on: 'top' },
        title: 'Save Changes',
        text: 'Saves your edits. The department list refreshes automatically.',
      },
    ]);
  }
});