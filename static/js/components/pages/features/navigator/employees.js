document.addEventListener('DOMContentLoaded', function () {

  // ── EMPLOYEE RECORDS PAGE ─────────────────────────────────
  if (document.getElementById('tableEmployeeRecords')) {
    const TOUR_KEY = 'tour_done_employees';

    let detailWasHidden = true;

    function ensureDetailVisible() {
      return new Promise(resolve => {
        const detail = document.getElementById('selectedEmployee');
        detailWasHidden = detail.classList.contains('d-none');
        document.getElementById('employeePlaceholder').classList.add('d-none');
        detail.classList.remove('d-none');
        resolve();
      });
    }

    function restoreDetail() {
      if (detailWasHidden) {
        document.getElementById('selectedEmployee').classList.add('d-none');
        document.getElementById('employeePlaceholder').classList.remove('d-none');
      }
    }

    let tourCheckedBox = null;

    function ensureBatchButtonVisible() {
      return new Promise(resolve => {
        const firstCheckbox = document.querySelector('.emp-select-checkbox:not(:disabled)');
        if (firstCheckbox && !firstCheckbox.checked) {
          firstCheckbox.checked = true;
          firstCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
          tourCheckedBox = firstCheckbox;
        }
        resolve();
      });
    }

    function restoreBatchButton() {
      if (tourCheckedBox) {
        tourCheckedBox.checked = false;
        tourCheckedBox.dispatchEvent(new Event('change', { bubbles: true }));
        tourCheckedBox = null;
      }
    }

    function openBsModal(id) {
      return new Promise(resolve => {
        const el = document.getElementById(id);
        if (el.classList.contains('show')) { resolve(); return; }
        el.addEventListener('shown.bs.modal', resolve, { once: true });
        if (id === 'modalResignEmployee') document.getElementById('btnOpenResign').click();
        else if (id === 'modalEditEmployee') document.getElementById('btnOpenEdit').click();
        else bootstrap.Modal.getOrCreateInstance(el).show();
      });
    }

    function closeBsModal(id) {
      return new Promise(resolve => {
        const el = document.getElementById(id);
        if (!el.classList.contains('show')) { resolve(); return; }
        el.addEventListener('hidden.bs.modal', resolve, { once: true });
        bootstrap.Modal.getInstance(el)?.hide();
      });
    }

    function cleanup() {
      document.querySelector('#modalEditEmployee [data-bs-dismiss="modal"]')?.click();
      restoreDetail();
      restoreBatchButton();
    }

    const tour = createTour([
      {
        id: 'emp-welcome',
        text: '<strong>Employee Records</strong><br>This tour walks you through the table, the detail panel, and how to edit or update an employee\'s status.',
        buttons: [
          { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
          { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
        ],
      },
      {
        id: 'emp-table',
        attachTo: { element: '#tableEmployeeRecords', on: 'top' },
        title: 'Employee Table',
        text: 'All registered employees are listed here. Click any row to load their full profile in the panel on the right.',
      },
      {
        id: 'emp-search',
        attachTo: { element: '#searchEmployeeInput', on: 'bottom' },
        title: 'Search',
        text: 'Filter the list in real time by typing a name or employee ID.',
      },
      {
        id: 'emp-status-filter',
        attachTo: { element: '#statusFilter', on: 'bottom' },
        title: 'Status Filter',
        text: 'Show only <strong>Active</strong>, <strong>Inactive</strong>, or <strong>Resigned</strong> employees. Defaults to Active on page load.',
      },
      {
        id: 'emp-batch-btn',
        attachTo: { element: '#btnBatchAdd', on: 'bottom' },
        title: 'Batch Import',
        text: 'Upload an <code>.xlsx</code> file to add multiple employees at once. Rows are validated before anything is saved.',
      },
      ...(document.getElementById('selectAllEmployees') ? [
        {
          id: 'emp-select-all',
          attachTo: { element: '#selectAllEmployees', on: 'right' },
          title: 'Select Multiple Employees',
          text: 'Check this box to select every visible employee at once. It only works while filtering by <strong>Active</strong> or <strong>Inactive</strong> status — not while showing all statuses or Resigned.',
        },
        {
          id: 'emp-batch-action-btn',
          attachTo: { element: '#btnBatchDeactivate', on: 'bottom' },
          title: 'Batch Set Inactive / Restore',
          text: 'Once employees are selected, this button appears. It sets all selected employees to <strong>Inactive</strong> at once, or <strong>Restores</strong> them to Active if the selected employees are already inactive. Their past attendance records are never affected — only future scheduling.',
          beforeShowPromise: ensureBatchButtonVisible,
        },
      ] : []),
      {
        id: 'emp-add-btn',
        attachTo: { element: '#btnAddEmployee', on: 'bottom' },
        title: 'Add Employee',
        text: 'Opens the single-employee registration form.',
      },
      {
        id: 'emp-placeholder',
        attachTo: { element: '#employeePlaceholder', on: 'left' },
        title: 'Detail Panel',
        text: 'Clicking a row loads that employee\'s full profile here — employment info, contact, and government IDs.',
      },
      {
        id: 'emp-detail',
        attachTo: { element: '#selectedEmployee', on: 'left' },
        title: 'Employee Profile Card',
        text: 'Shows the employee\'s name, ID, status badge, and tabbed details. Switch between <strong>Employment</strong>, <strong>Contact</strong>, and <strong>Gov. IDs</strong> tabs.',
        beforeShowPromise: ensureDetailVisible,
      },
      {
        id: 'emp-resign-btn',
        attachTo: { element: '#btnOpenResign', on: 'top' },
        title: 'Mark as Resigned / Restore',
        text: 'Toggles the employee\'s resigned status. If already resigned, this button switches to <strong>Restore Employee</strong>.',
      },
      {
        id: 'emp-resign-modal',
        attachTo: { element: '#btnOpenResign', on: 'top' },
        title: 'Resignation Confirmation',
        text: 'Clicking this button opens a confirmation dialog before any change is made. The button label and color update dynamically based on the employee\'s current status.',
      },
      {
        id: 'emp-edit-btn',
        attachTo: { element: '#btnOpenEdit', on: 'top' },
        title: 'Edit Employee Details',
        text: 'Opens the edit form pre-filled with the employee\'s current data across three tabs.',
      },
      {
        id: 'emp-edit-tabs',
        attachTo: { element: '#modalEditEmployee .nav-tabs', on: 'bottom' },
        title: 'Three-Tab Form',
        text: 'Employee details are split into three tabs. Click each to switch sections.',
        beforeShowPromise: () => openBsModal('modalEditEmployee'),
      },
      {
        id: 'emp-edit-basic',
        attachTo: { element: '#modalEditEmployee a[href="#tabEmpBasic"]', on: 'bottom' },
        title: 'Basic Info',
        text: 'Edit the employee\'s name, birthday, hire date, regularization date, department, and position.',
        beforeShowPromise: () => new Promise(resolve => {
          document.querySelector('#modalEditEmployee a[href="#tabEmpBasic"]').click();
          setTimeout(resolve, 200);
        }),
      },
      {
        id: 'emp-edit-contact',
        attachTo: { element: '#modalEditEmployee a[href="#tabEmpContact"]', on: 'bottom' },
        title: 'Contact Tab',
        text: 'Update phone number, home address, and emergency contact details.',
        beforeShowPromise: () => new Promise(resolve => {
          document.querySelector('#modalEditEmployee a[href="#tabEmpContact"]').click();
          setTimeout(resolve, 200);
        }),
      },
      {
        id: 'emp-edit-govids',
        attachTo: { element: '#modalEditEmployee a[href="#tabEmpGovIds"]', on: 'bottom' },
        title: 'Gov. IDs Tab',
        text: 'Store TIN, SSS, PhilHealth, and Pag-IBIG numbers.',
        beforeShowPromise: () => new Promise(resolve => {
          document.querySelector('#modalEditEmployee a[href="#tabEmpGovIds"]').click();
          setTimeout(resolve, 200);
        }),
      },
      {
        id: 'emp-edit-save',
        attachTo: { element: '#btnEditEmployee', on: 'top' },
        title: 'Save Changes',
        text: 'Saves all edits. Any validation errors appear at the top of the form.',
      },
    ]);

    tour.on('complete', cleanup);
    tour.on('cancel',   cleanup);

    autoStartTour(TOUR_KEY, tour);
    document.getElementById('emp-btn-help-tour')
      .addEventListener('click', () => startTour(TOUR_KEY, tour));
  }


  // ── ADD EMPLOYEE PAGE ──────────────────────────────────────
  if (document.getElementById('card-basic-info')) {
    const TOUR_KEY = 'tour_done_add_employee';

    const tour = createTour([
      {
        id: 'add-welcome',
        text: '<strong>Add New Employee</strong><br>Fill in this form to register a new employee. Fields marked with <span class="text-red">*</span> are required.',
        buttons: [
          { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
          { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
        ],
      },
      {
        id: 'add-basic',
        attachTo: { element: '#card-basic-info', on: 'right' },
        title: 'Basic Information',
        text: 'Enter the employee\'s full legal name and date of birth. First and last name are required.',
      },
      {
        id: 'add-employment',
        attachTo: { element: '#card-employment', on: 'right' },
        title: 'Employment Details',
        text: 'Assign an employee ID, department, and position. The position dropdown enables only after a department is selected. Hire and regularization dates are optional.',
      },
      {
        id: 'add-contact',
        attachTo: { element: '#card-contact', on: 'right' },
        title: 'Contact Information',
        text: 'Optionally provide a contact number, home address, and emergency contact details.',
      },
      {
        id: 'add-govid',
        attachTo: { element: '#card-govid', on: 'right' },
        title: 'Government IDs',
        text: 'Record TIN, SSS, PhilHealth, and Pag-IBIG numbers. All optional — can be added later via Edit Details.',
      },
      {
        id: 'add-status',
        attachTo: { element: '#card-status', on: 'left' },
        title: 'Employee Status',
        text: 'New employees are <strong>Active</strong> by default. Uncheck to save as inactive.',
      },
      {
        id: 'add-group',
        attachTo: { element: '#card-group', on: 'left' },
        title: 'Employee Group',
        text: 'Optionally assign the employee to a group. Groups are used for overtime exemption rules.',
      },
      {
        id: 'add-actions',
        attachTo: { element: '#card-actions', on: 'left' },
        title: 'Save or Cancel',
        text: 'Click <strong>Save Employee</strong> to register. Contact info, IDs, and other details can always be added later from Employee Records.',
      },
    ]);

    autoStartTour(TOUR_KEY, tour);
    document.getElementById('add-emp-btn-help-tour')
      .addEventListener('click', () => startTour(TOUR_KEY, tour));
  }


  // ── BATCH ADD PAGE ─────────────────────────────────────────
  if (document.getElementById('drop-zone')) {
    const TOUR_KEY = 'tour_done_batch_add';

    const tour = createTour([
      {
        id: 'batch-welcome',
        text: '<strong>Batch Employee Import</strong><br>Import multiple employees at once from an Excel file in two steps: upload, then review and confirm.',
        buttons: [
          { text: 'Skip',       classes: 'btn btn-md btn-ghost-secondary', action: () => tour.cancel() },
          { text: 'Start Tour', classes: 'btn btn-md btn-primary',         action: () => tour.next()   },
        ],
      },
      {
        id: 'batch-upload-section',
        attachTo: { element: '#step-upload', on: 'top' },
        title: 'Step 1 — Upload',
        text: 'Download the Excel template, fill it in with your employee data, then upload it here. The column guide on the right shows all expected fields and which are required.',
      },
      {
        id: 'batch-drop',
        attachTo: { element: '#drop-zone', on: 'top' },
        title: 'File Drop Zone',
        text: 'Drag and drop your <code>.xlsx</code> file here, or click <strong>browse</strong> to select it from your computer. Only <code>.xlsx</code> files are accepted.',
      },
      {
        id: 'batch-parse',
        attachTo: { element: '#btn-parse', on: 'top' },
        title: 'Parse & Preview',
        text: 'Validates every row in the file and shows a preview. Valid rows are importable, warning rows import with some blank fields, and error rows are skipped. Nothing is saved until you confirm.',
      },
    ]);

    autoStartTour(TOUR_KEY, tour);
    document.getElementById('batch-btn-help-tour')
      .addEventListener('click', () => startTour(TOUR_KEY, tour));
  }

});