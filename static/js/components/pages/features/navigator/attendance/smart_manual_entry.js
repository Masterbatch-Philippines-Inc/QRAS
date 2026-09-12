document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_smart_manual_attendance';

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Smart Manual Attendance</strong><br>Upload a scanned PDF attendance sheet and the system will extract entries and map them to employee records automatically.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'pdf-input',
      attachTo: { element: '#pdfInput', on: 'bottom' },
      title: 'PDF Upload',
      text: 'Select a PDF attendance sheet. Each page is treated as one day — multi-page PDFs are fully supported.',
    },
    {
      id: 'parse-btn',
      attachTo: { element: '#parseBtn', on: 'bottom' },
      title: 'Parse PDF',
      text: 'Sends the PDF to the server for text extraction and employee name matching. Rows the system cannot match will be flagged as Unmatched.',
    },
    {
      id: 'summary-bar',
      title: 'Match Summary',
      text: '<strong>Matched</strong> — employee found in the system.<br><strong>Unmatched</strong> — name not recognised; assign the employee manually using the dropdown on each flagged row.<br><strong>Skipped</strong> — rows you marked to exclude.',
    },
    {
      id: 'save-btn',
      title: 'Save All Records',
      text: 'Commits all matched, non-skipped entries to the database. This button stays disabled until every Unmatched row is resolved.',
    },
  ]);

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('smart-att-help-btn')
    .addEventListener('click', () => startTour(TOUR_KEY, tour));
});