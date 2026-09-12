document.addEventListener('DOMContentLoaded', function () {
  const TOUR_KEY = 'tour_done_ot_approval';

  const otModalEl = document.getElementById('otManageModal');
  const otModal    = tabler.Modal.getOrCreateInstance(otModalEl);

  const tour = createTour([
    {
      id: 'welcome',
      text: '<strong>Overtime Approvals</strong><br>Review employees with detected overtime and approve or reject each request.',
      buttons: [
        { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
        { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
      ],
    },
    {
      id: 'ot-search',
      attachTo: { element: '#ot-search', on: 'bottom' },
      title: 'Search',
      text: 'Search by employee name to quickly narrow the list.',
    },
    {
      id: 'ot-table',
      attachTo: { element: '#ot-table thead', on: 'bottom' },
      title: 'Overtime Records',
      text: 'Each row shows the employee, date, clocked time in/out, and current status. Records already decided show <strong>Decided</strong> instead of a Manage button.',
    },
    {
      id: 'ot-action',
      attachTo: { element: '#ot-table thead th:nth-child(6)', on: 'bottom' },
      title: 'Manage Action',
      text: 'Click <strong>Manage</strong> on a pending row to open the approval modal.',
      when: {
        show: () => otModal.show(),
      },
    },
    {
      id: 'ot-type',
      attachTo: { element: '#ot-types-elements', on: 'bottom' },
      title: 'OT Type',
      text: 'Choose Pre-Shift or Post-Shift. If the record only qualifies for one type, it\'s auto-selected for you.',
    },
    {
      id: 'ot-times',
      attachTo: { element: '#ot-startEnd-elements', on: 'bottom' },
      title: 'OT Start / End',
      text: 'Start and end times are pre-filled based on the selected type, but can be adjusted manually.',
    },
    {
      id: 'ot-hours',
      attachTo: { element: '#ot-modal-hours', on: 'bottom' },
      title: 'OT Hours',
      text: 'Automatically computed from Start and End — this is the value saved on approval.',
    },
    {
      id: 'ot-remarks',
      attachTo: { element: '#ot-modal-remarks', on: 'top' },
      title: 'Remarks',
      text: 'Optional notes for the decision, visible later on the record.',
    },
    {
      id: 'ot-decision',
      attachTo: { element: '#otManageModal .modal-footer', on: 'top' },
      title: 'Approve or Reject',
      text: 'Approve saves the OT hours and type. Reject discards the request — both are final and reflected immediately on the row.',
      when: {
        hide: () => otModal.hide(),
      },
    },
    {
      id: 'pagination',
      attachTo: { element: '.card-footer', on: 'top' },
      title: 'Records Per Page',
      text: 'Adjust how many records are shown per page, and navigate using the pagination controls.',
    },
  ]);

  tour.on('cancel',   () => otModal.hide());
  tour.on('complete', () => otModal.hide());

  otModalEl.addEventListener('hidden.bs.modal', () => {
    document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
  });

  autoStartTour(TOUR_KEY, tour);

  document.getElementById('ot-btn-help-tour')
    ?.addEventListener('click', () => startTour(TOUR_KEY, tour));
});