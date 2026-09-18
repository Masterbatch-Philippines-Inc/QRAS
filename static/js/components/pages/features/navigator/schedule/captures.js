document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_scan_captures';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Welcome to Scan Captures!</strong><br>This quick tour walks you through everything on this page.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'date-range',
      attachTo: { element: '#scan-daterange', on: 'bottom' },
      title: 'Date Range Filter',
      text: 'Use this to set the date range you want to view. The capture counts in the table will update automatically based on the range you select. It defaults to the current month.',
    },
    {
      id: 'search',
      attachTo: { element: '#scan-search', on: 'bottom' },
      title: 'Search Employee',
      text: 'Type an employee name, department, or position to quickly find who you are looking for.',
    },
    {
      id: 'employee-table',
      attachTo: { element: '#scan-emp-table', on: 'top' },
      title: 'Employee List',
      text: 'This table lists all active employees. The <strong>Captures in Range</strong> column shows how many scan photos exist for each employee within the selected date range. A dash means no captures were recorded.',
    },
    {
      id: 'employee-row',
      attachTo: { element: '.scan-emp-row', on: 'bottom' },
      title: 'Click to View Captures',
      text: 'Click any employee row to open their capture records. You will see each scan photo organized by date, along with the time and whether it was a time-in or time-out.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  const helpBtn = document.getElementById('scan-captures-btn-help-tour');
  if (helpBtn) {
    helpBtn.addEventListener('click', () => startTour(TOUR_KEY, tour));
  }

  // ── Capture Modal Tour ─────────────────────────────────────────────────────
  const MODAL_TOUR_KEY = 'tour_done_scan_capture_modal';

  const modalTour = createTour([
    {
      id: 'modal-welcome',
      text: '<strong>Scan Capture Records</strong><br>This modal shows all scan photos for the selected employee within the chosen date range.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => modalTour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => modalTour.next()   },
      ],
    },
    {
      id: 'modal-header',
      attachTo: { element: '#captureModal .modal-header', on: 'bottom' },
      title: 'Employee & Range',
      text: 'Shows the employee name, the date range being viewed, and the total number of captures found.',
    },
    {
      id: 'modal-table',
      attachTo: { element: '#captureModal .table', on: 'top' },
      title: 'Capture Records',
      text: 'Each row is one scan event. <strong>Date</strong> and <strong>Time</strong> show when it was recorded. <strong>Scan Type</strong> indicates whether it was a Time In or Time Out.',
    },
    {
      id: 'modal-view-btn',
      attachTo: { element: '#captureModal .btn-view-capture', on: 'left' },
      title: 'View Photo',
      text: 'Click <strong>View</strong> to open the actual scan photo. The capture modal will close and the photo will open in a separate viewer with metadata.',
      canClickTarget: false,
    },
    {
      id: 'modal-pagination',
      attachTo: { element: '#capture-modal-pagination', on: 'top' },
      title: 'Pagination',
      text: 'If there are many records, use these controls to navigate between pages. You can also change how many records appear per page using the dropdown on the left.',
    },
  ]);

  const modalHelpBtn = document.getElementById('capture-modal-help-btn');
  if (modalHelpBtn) {
    modalHelpBtn.addEventListener('click', () => startTour(MODAL_TOUR_KEY, modalTour));
  }
});

