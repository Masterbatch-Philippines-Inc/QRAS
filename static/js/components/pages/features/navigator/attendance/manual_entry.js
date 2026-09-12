document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_manual_attendance';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Manual Attendance Entry</strong><br>Record time-in or time-out entries for one or more employees at once without using a QR scan.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'ready-badge',
      attachTo: { element: '#readyBadge', on: 'bottom' },
      title: 'Ready Count',
      text: 'Tracks how many rows are fully filled out and ready to save. A row is ready when it has an employee, date, time, and In/Out type.',
    },
    {
      id: 'entry-rows',
      attachTo: { element: '#rowsContainer', on: 'top' },
      title: 'Entry Rows',
      text: 'Each row is one attendance log entry. Fill in the employee, date, time, and select Time In or Time Out.',
    },
    {
      id: 'status-dot',
      attachTo: { element: '#rowsContainer', on: 'left' },
      title: 'Row Status Dot',
      text: 'The small circle on the left of each row turns <strong>green</strong> when all fields are complete, and stays <strong>grey</strong> when something is missing.',
    },
    {
      id: 'in-out-toggle',
      attachTo: { element: '#rowsContainer', on: 'right' },
      title: 'Time In / Time Out',
      text: 'Select <strong>In</strong> for a clock-in log or <strong>Out</strong> for a clock-out log. File separate rows if an employee needs both recorded.',
    },
    {
      id: 'clear-btn',
      attachTo: { element: '#clearEntriesBtn', on: 'bottom' },
      title: 'Clear All',
      text: 'Wipes all current rows and resets the form to a single blank entry.',
    },
    {
      id: 'save-btn',
      attachTo: { element: '#saveEntriesBtn', on: 'bottom' },
      title: 'Save Entries',
      text: 'Validates all rows and submits them at once. Rows with missing fields are flagged before anything is saved.',
    },
    {
      id: 'preview-card',
      title: 'Entry Preview',
      text: 'Once rows are complete, a live preview table appears below the form so you can verify all entries before saving.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('manual-att-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));
});