document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_settings_system_users';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>System Users</strong><br>Manage accounts for admin staff, department heads, and approvers. Each user has a role that controls what they can see and do.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'search',
      attachTo: { element: '#sys-users-search', on: 'bottom' },
      title: 'Search',
      text: 'Filter by name, email, or role.',
    },
    {
      id: 'inactive-toggle',
      attachTo: { element: 'input[name="show_inactive"]', on: 'bottom' },
      title: 'Show Deactivated',
      text: 'Toggle to include deactivated user accounts. Deactivated users cannot log in.',
    },
    {
      id: 'add-user-btn',
      attachTo: { element: '[data-bs-target="#addUserModal"]', on: 'bottom' },
      title: 'Add System User',
      text: 'Creates a new system account. A username and temporary password are auto-generated and emailed to the user.',
    },
    {
      id: 'table',
      attachTo: { element: '#tours-sysusers-rec', on: 'bottom' },
      title: 'System User Records',
      text: 'Shows each user\'s name, email, assigned role, and login status. A green <em>Logged In</em> label means they have an active session right now.',
    },
    {
      id: 'actions',
      title: 'Row Actions',
      text: '<strong>Edit</strong> — change role, email, department, or linked employee.<br><strong>Reset Password</strong> — generates a new password and emails it to the user.<br><strong>Deactivate / Restore</strong> — soft-deletes the account without permanently removing it.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('tours-sys-users-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));

  // ── Modal tours (wire up when modal HTML files are available) ──────────────

  function addUserModalTour() {
    return createTour([
      {
        id: 'add-name',
        title: 'Name Fields',
        text: 'Enter the user\'s first and last name. This is what appears throughout the system.',
      },
      {
        id: 'add-role',
        attachTo: { element: '#addRole', on: 'bottom' },
        title: 'Role',
        text: 'Assign a system role. The role determines which modules the user can access. Selecting <strong>Department Head</strong> reveals a department picker.',
      },
      {
        id: 'add-dept',
        title: 'Department (Dept. Head only)',
        text: 'Required when the role is Department Head. This scopes all their views to the selected department automatically.',
      },
      {
        id: 'add-employee',
        attachTo: { element: '#addEmployee', on: 'bottom' },
        title: 'Linked Employee',
        text: 'Optionally link the user account to an employee record. Required for Department Heads to be excluded from their own approval queues.',
      },
      {
        id: 'add-email',
        attachTo: { element: '#addEmail', on: 'bottom' },
        title: 'Email',
        text: 'Login credentials are sent here. If email delivery fails, the account is still created and you\'ll see a warning.',
      },
    ]);
  }

  function editUserModalTour() {
    return createTour([
      {
        id: 'edit-role',
        attachTo: { element: '#editRole', on: 'bottom' },
        title: 'Role',
        text: 'Change the user\'s system role. Removing the Department Head role from a user with pending approvals will trigger a confirmation warning.',
      },
      {
        id: 'edit-email',
        attachTo: { element: '#editEmail', on: 'bottom' },
        title: 'Email',
        text: 'Update the account email. This is used for password resets and system notifications.',
      },
      {
        id: 'edit-employee',
        attachTo: { element: '#editEmployee', on: 'bottom' },
        title: 'Linked Employee',
        text: 'Re-link or unlink the employee record associated with this system account.',
      },
    ]);
  }

  function resetPasswordModalTour() {
    return createTour([
      {
        id: 'reset-info',
        title: 'Reset Password',
        text: 'Generates a new random password and emails it to the user. The old password is immediately invalidated. If email fails, a warning is shown and the new password must be shared manually.',
      },
    ]);
  }
});