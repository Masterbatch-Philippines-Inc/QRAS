document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_schedules';

  // ── Main page tour ────────────────────────────────────────────────────────
  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Welcome to Schedule Management!</strong><br>This tour walks you through creating shift schedules and assigning them to employees.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'btn-add-schedule',
      attachTo: { element: '#btn-add-schedule', on: 'bottom' },
      title: 'New Schedule',
      text: 'Click here to open the schedule form. You\'ll define shift times, night differential windows, and which days are rest days.',
    },
    {
      id: 'schedule-search',
      attachTo: { element: '#schedule-search-input', on: 'bottom' },
      title: 'Search Schedules',
      text: 'Filter the schedule list by name to quickly find a specific shift.',
    },
    {
      id: 'schedule-table',
      attachTo: { element: '#schedule-table', on: 'top' },
      title: 'Shift Schedules',
      text: 'All schedules are listed here with their shift window, covered specific dates, and status. The creator and their department are shown under each schedule name. Use <strong>Edit</strong> to modify a schedule. Admins can <strong>Deactivate</strong> or restore a schedule — deactivated schedules are preserved and can be re-enabled anytime.',
    },
    {
      id: 'assign-schedule-select',
      attachTo: { element: '#assign-schedule-select', on: 'top' },
      title: 'Select a Schedule',
      text: 'Pick the shift you want to assign. Only active schedules appear in this list.',
    },
    {
      id: 'employee-filter',
      attachTo: { element: '#employee-filter', on: 'bottom' },
      title: 'Filter Employees',
      text: 'Type here to narrow the employee list below by name, department, or position.',
    },
    {
      id: 'select-all-btns',
      attachTo: { element: '#btn-tour-select-all', on: 'bottom' },
      title: 'Select / Deselect All',
      text: 'Quickly select or clear all <em>visible</em> employees at once — handy when you\'ve already filtered the list.',
    },
    {
      id: 'employee-list',
      attachTo: { element: '#employee-list', on: 'top' },
      title: 'Employee List',
      text: 'Check the employees you want to assign. Employees already on a schedule show their current shift in the <em>Employee Group</em> column — you can <strong>Unassign</strong> them from here without leaving the page.',
    },
    {
      id: 'btn-assign',
      attachTo: { element: '#btn-assign', on: 'top' },
      title: 'Assign Schedule',
      text: 'Enabled once you\'ve selected a schedule and at least one employee. Existing attendance records are <em>not</em> recomputed on assignment from this panel — use the Unscheduled page for that.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('schedules-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));

  // ── Add / Edit Schedule modal tour ────────────────────────────────────────
  const scheduleModal = document.getElementById('addEditscheduleModal');
  if (scheduleModal) {
    const MODAL_KEY = 'tour_done_add_schedule_modal';
    let modalTourFired = false;

    scheduleModal.addEventListener('shown.bs.modal', function () {
      const globalStep = document.getElementById('sched-is-global') ? [{
        id: 'modal-is-global',
        attachTo: { element: '#modal-is-global', on: 'right' },
        title: 'Global Schedule',
        text: 'Admin only. When marked as Global, this schedule becomes visible to all department heads. They can view and assign it to their employees but cannot edit or deactivate it.',
        canClickTarget: false,
      }] : []
      const modalTour = createTour([
        {
          id: 'modal-welcome',
          text: '<strong>Schedule Form</strong><br>Fill in the fields below to create or update a shift schedule.',
          buttons: [
            { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => modalTour.cancel() },
            { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => modalTour.next()   },
          ],
        },
        {
          id: 'modal-sched-name',
          attachTo: { element: '#modal-sched-name', on: 'bottom' },
          title: 'Schedule Name',
          text: 'Give this shift a clear, recognisable name — e.g. <em>Day Shift 8–5</em> or <em>Night Shift 10–6</em>.',
        },
        {
          id: 'modal-shift-times',
          attachTo: { element: '#modal-shift-times', on: 'bottom' },
          title: 'Shift Start & End',
          text: 'Set the official shift window. These times drive late-arrival detection, undertime, and overtime computation for every employee on this schedule.',
        },
        {
          id: 'modal-crosses-midnight',
          attachTo: { element: '#modal-crosses-midnight', on: 'right' },
          title: 'Crosses Midnight',
          text: 'Enable for shifts that span midnight (e.g. 10 PM – 6 AM). When ticked, night differential from <strong>10:00 PM to 6:00 AM</strong> is automatically applied as required by the Philippine Labor Code (Art. 86) — no manual input needed.',
        },
        {
          id: 'modal-rest-days',
          attachTo: { element: '#modal-rest-days', on: 'bottom' },
          title: 'Rest Days',
          text: 'Select at least one rest day — required. Employees on this schedule are excluded from absence reports and recomputation on their designated rest days.',
        },
        {
          id: 'modal-specific-dates',
          attachTo: { element: '#modal-specific-dates', on: 'left' },
          title: 'Specific Dates',
          text: 'Click any date on the calendar to include it. Use the shortcut buttons — Today, This Week, Next Week, This Month, Next Month — or the weekday toggles to add dates in bulk. Shift+Click two dates to fill a range. Past dates are disabled.',
        },
        {
          id: 'modal-is-active',
          attachTo: { element: '#modal-is-active', on: 'right' },
          title: 'Active Toggle',
          text: 'Admins can toggle this. Inactive schedules cannot be assigned to new employees but all existing records tied to them are preserved. Department heads cannot change this field.',
        },
        ...globalStep,
        {
          id: 'btn-save-schedule',
          attachTo: { element: '#btn-save-schedule', on: 'top' },
          title: 'Save Schedule',
          text: 'Saves the schedule. Required fields: Name, Shift Start, Shift End, and at least one Rest Day.',
        },
      ]);

      modalTour.on('complete', () => localStorage.setItem(MODAL_KEY, '1'));
      modalTour.on('cancel',   () => localStorage.setItem(MODAL_KEY, '1'));

      const helpBtn = document.getElementById('sched-modal-help-tour')
      if (helpBtn) {
        helpBtn.onclick = (e) => { e.preventDefault(); modalTour.start() }
      }

      if (modalTourFired || localStorage.getItem(MODAL_KEY)) return;
      modalTourFired = true;
      modalTour.start();
    });
  }

  // ── Unassign Schedule modal tour ──────────────────────────────────────────
  const unassignModal = document.getElementById('unassignScheduleModal');
  if (unassignModal) {
    const UNASSIGN_KEY = 'tour_done_unassign_modal';
    let unassignTourFired = false;

    unassignModal.addEventListener('shown.bs.modal', function () {
      if (unassignTourFired || localStorage.getItem(UNASSIGN_KEY)) return;
      unassignTourFired = true;

      const unassignTour = createTour([
        {
          id: 'unassign-body',
          attachTo: { element: '#unassignScheduleModal .modal-body', on: 'bottom' },
          title: 'Confirm Unassign',
          text: 'This dialog confirms which employee and schedule you\'re removing. Past attendance records for this employee are untouched — they will simply have no schedule going forward.',
          buttons: [
            { text: 'Skip', classes: 'btn btn-md btn-ghost-secondary', action: () => unassignTour.cancel() },
            { text: 'Next', classes: 'btn btn-md btn-primary',         action: () => unassignTour.next()   },
          ],
        },
        {
          id: 'unassign-confirm-btn',
          attachTo: { element: '#btn-confirm-unassign-sched', on: 'top' },
          title: 'Remove Button',
          text: 'Click <strong>Remove</strong> to confirm, or <strong>Cancel</strong> to go back without making any changes.',
        },
      ]);

      unassignTour.on('complete', () => localStorage.setItem(UNASSIGN_KEY, '1'));
      unassignTour.on('cancel',   () => localStorage.setItem(UNASSIGN_KEY, '1'));
      unassignTour.start();
    });
  }
});