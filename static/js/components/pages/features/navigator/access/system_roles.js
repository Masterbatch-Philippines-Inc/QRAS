document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_settings_roles';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>System Roles</strong><br>Roles control what each user can see and do. Every role has per-module CRUD permissions that can be freely configured — except the Admin role.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'search',
      attachTo: { element: '#roles-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter roles by name.',
    },
    {
      id: 'inactive-toggle',
      attachTo: { element: 'input[name="show_inactive"]', on: 'bottom' },
      title: 'Show Inactive',
      text: 'Toggle to include deactivated roles. Users assigned an inactive role lose access until it is restored or they are reassigned.',
    },
    {
      id: 'add-role-btn',
      attachTo: { element: '[data-bs-target="#addRoleModal"]', on: 'bottom' },
      title: 'Add Role',
      text: 'Creates a new role with a blank permission set. You\'ll configure its module access in the Edit dialog.',
    },
    {
      id: 'table',
      attachTo: { element: '#tours-roles-rec', on: 'bottom' },
      title: 'Role Records',
      text: 'Lists all roles and how many system users are assigned to each. Click the user count to view and manage who is assigned to that role.',
    },
    {
      id: 'edit-btn',
      attachTo: { element: '#edit-roles-btn', on: 'left' },
      title: 'Edit Permissions',
      text: 'Opens the permission matrix for the role. You can toggle Create, Read, Update, and Delete per module, or use the column headers to toggle an entire permission type at once.',
    },
    {
      id: 'admin-note',
      title: 'Admin Role',
      text: 'The Admin role always has full access to all modules and cannot be deactivated or have its permissions modified.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('tours-roles-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));

  // ── Modal tours (wire up when modal HTML files are available) ──────────────

  function addRoleModalTour() {
    return createTour([
      {
        id: 'add-role-name',
        attachTo: { element: '#addRoleName', on: 'bottom' },
        title: 'Role Name',
        text: 'A unique name for this role (e.g. Admin Approver, HR Staff). Use the Edit dialog after creation to configure its permissions.',
      },
    ]);
  }

  function editRoleModalTour() {
    return createTour([
      {
        id: 'edit-role-name',
        attachTo: { element: '#editRoleName', on: 'bottom' },
        title: 'Role Name',
        text: 'Rename the role. Disabled for the Admin role.',
      },
      {
        id: 'perm-matrix',
        attachTo: { element: '#editRoleBody', on: 'top' },
        title: 'Permission Matrix',
        text: 'Each row is a system module. Tick <strong>Create / Read / Update / Delete</strong> to grant that action. The <strong>All</strong> column is a row-level shortcut to toggle all four at once.',
      },
      {
        id: 'col-headers',
        title: 'Column Shortcuts',
        text: 'The header checkboxes toggle an entire permission type (e.g. all Read permissions at once) across every module.',
      },
      {
        id: 'edit-role-save',
        attachTo: { element: '#editRoleBtn', on: 'top' },
        title: 'Update Permissions',
        text: 'Saves the full permission set. Changes take effect on the user\'s next page load.',
      },
    ]);
  }

  function roleUsersModalTour() {
    return createTour([
      {
        id: 'users-list',
        attachTo: { element: '#roleUsersBody', on: 'top' },
        title: 'Assigned Users',
        text: 'Lists all active system users. Checked rows are currently assigned to this role.',
      },
      {
        id: 'select-all',
        attachTo: { element: '#roleUsersSelectAll', on: 'right' },
        title: 'Select All',
        text: 'Checks all users at once for bulk role assignment.',
      },
      {
        id: 'users-save',
        attachTo: { element: '#roleUsersBtn', on: 'top' },
        title: 'Update Assigned Users',
        text: 'Saves the assignment. Users unchecked here will have their role cleared.',
      },
    ]);
  }
});