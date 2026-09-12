document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_settings_employee_groups';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Employee Groups</strong><br>Groups control OT filing exemption policies. Assign employees to a group to apply the correct overtime rules automatically.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'group-table',
      attachTo: { element: '#tours-empgrp-rec', on: 'bottom' },
      title: 'Group Records',
      text: 'Lists all employee groups. The <strong>OT Exempted</strong> column indicates whether members of the group are exempt from filing overtime requests.',
    },
    {
      id: 'new-group-btn',
      attachTo: { element: '[data-bs-target="#modalCreateGroup"]', on: 'bottom' },
      title: 'New Group',
      text: 'Creates a new group. You\'ll name it and set whether members are OT-filing exempted.',
    },
    {
      id: 'assign-panel',
      attachTo: { element: '#assign-group-select', on: 'bottom' },
      title: 'Assign Group',
      text: 'Select a group here, then pick one or more employees from the list below and click <strong>Assign Group</strong>.',
    },
    {
      id: 'employee-filter',
      attachTo: { element: '#employee-filter', on: 'bottom' },
      title: 'Filter Employees',
      text: 'Type to filter the employee list by name, department, or position.',
    },
    {
      id: 'select-all',
      attachTo: { element: '#btn-select-all', on: 'bottom' },
      title: 'Select / Deselect All',
      text: 'Quickly check or uncheck all visible employees in the list.',
    },
    {
      id: 'unassign',
      title: 'Unassign',
      text: 'Each employee row shows their current group. Click <strong>Unassign</strong> to remove them from that group before assigning a new one.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('tours-empgrp-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));

  // ── Modal tours (wire up when modal HTML files are available) ──────────────

  function createGroupModalTour() {
    return createTour([
      {
        id: 'create-name',
        attachTo: { element: '#createGroupName', on: 'bottom' },
        title: 'Group Name',
        text: 'A descriptive name for the group (e.g. Rank & File, Supervisors, Guards).',
      },
      {
        id: 'create-ot',
        attachTo: { element: '#createGroupOt', on: 'right' },
        title: 'OT Filing Exempted',
        text: 'When checked, members of this group do not need to file overtime requests — their OT is automatically credited.',
      },
      {
        id: 'create-save',
        attachTo: { element: '#btnCreateGroup', on: 'top' },
        title: 'Save',
        text: 'Creates the group. You can then assign employees to it from the Assign Group panel.',
      },
    ]);
  }

  function editGroupModalTour() {
    return createTour([
      {
        id: 'edit-name',
        attachTo: { element: '#editGroupName', on: 'bottom' },
        title: 'Group Name',
        text: 'Rename the group. Existing members stay assigned.',
      },
      {
        id: 'edit-ot',
        attachTo: { element: '#editGroupOt', on: 'right' },
        title: 'OT Filing Exempted',
        text: 'Toggle the exemption policy. Changing this affects how overtime is handled for all members going forward.',
      },
      {
        id: 'edit-save',
        attachTo: { element: '#btnEditGroup', on: 'top' },
        title: 'Save Changes',
        text: 'Applies your edits immediately.',
      },
    ]);
  }

  function unassignGroupModalTour() {
    return createTour([
      {
        id: 'unassign-info',
        title: 'Unassign Confirmation',
        text: 'Confirms removing the employee from their current group. The employee will have no group until manually reassigned.',
      },
    ]);
  }
});