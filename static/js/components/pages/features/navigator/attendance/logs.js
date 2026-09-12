document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY       = 'tour_done_attendance_records';
  const MODAL_TOUR_KEY = 'tour_done_att_logs_modal';

  // ── Main page tour ────────────────────────────────────────────────────────
  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Attendance Logs</strong><br>This page shows every employee\'s latest attendance record and any pending request statuses.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'search',
      attachTo: { element: '#main-attendance-table', on: 'bottom' },
      title: 'Search',
      text: 'Filter the list by employee name or department as you type.',
    },
    {
      id: 'table',
      attachTo: { element: '#attendance-table', on: 'top' },
      title: 'Attendance Table',
      text: 'Each row is one employee. Columns show their department, last recorded date (with holiday badges if applicable), and pending request status.',
    },
    {
      id: 'pending-col',
      attachTo: { element: '#att-pending-col', on: 'top' },
      title: 'Pending Approvals',
      text: 'Badges here indicate outstanding Overtime, Undertime, or Half-day requests for that employee that still need a decision.',
    },
    {
      id: 'row-click',
      attachTo: { element: '#attendance-table', on: 'top' },
      title: 'View Detailed Logs',
      text: 'Click any row to open the employee\'s full attendance log — daily time-in/out pairs, computed hours, and approval status per record.',
    },
    {
      id: 'pagination',
      attachTo: { element: '#attendance-table-pagination', on: 'top' },
      title: 'Pagination',
      text: 'Navigate pages here. Use the records-per-page dropdown on the left to adjust how many rows are shown at once.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('att-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));

  // ── Modal tour ────────────────────────────────────────────────────────────
  const modal = document.getElementById('employeeAttendanceLogs');
  if (!modal) return;

  function buildModalTour() {
    const mt = createTour([
      {
        id: 'modal-header',
        attachTo: { element: '#att-modal-header', on: 'bottom' },
        title: 'Employee Logs',
        text: 'Shows the full attendance history for the selected employee. The subtitle summarises how many records are approved, pending, rejected, or not yet complete.',
      },
      {
        id: 'modal-table',
        attachTo: { element: '#att-modal-table', on: 'top' },
        title: 'Log Table',
        text: '<strong>Date</strong> — the work date.<br><strong>Time In / Out</strong> — raw clock timestamps.<br><strong>Total Hrs Worked</strong> — computed hours after break deduction.<br><strong>Status</strong> and <strong>Remarks</strong> ',
      },
      {
        id: 'modal-status-col',
        attachTo: { element: '#att-modal-status-col', on: 'bottom' },
        title: 'Status Column',
        text: '<strong>Complete</strong> — clean shift, no issues.<br><strong>Incomplete</strong> — with missings logs.',
      },
      {
        id: 'modal-remarks-col',
        attachTo: { element: '#att-modal-remarks-col', on: 'bottom' },
        title: 'Remarks Column',
        text: 'Shows computed flags such as Credited hours, Overtime, Undertime, Late, Half-day, Missing Logs, or Unscheduled. Empty while the shift is still in progress.',
      },
    ]);
    return mt;
  }

  modal.addEventListener('shown.bs.modal', function () {
    if (!localStorage.getItem(MODAL_TOUR_KEY)) {
      startTour(MODAL_TOUR_KEY, buildModalTour());
    }
  });

  document.getElementById('att-modal-help-btn')
    .addEventListener('click', () => startTour(MODAL_TOUR_KEY, buildModalTour()));
});