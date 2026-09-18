// ════════════════════════════════════════════
//   MAIN TABLE — search + pagination
// ════════════════════════════════════════════
function initTableController(config) {
  const searchEl = document.getElementById(config.searchId);
  const pageEl   = document.getElementById(config.pageCountId);
  const paginEl  = document.getElementById(config.paginId);
  let rows       = Array.from(document.querySelectorAll(config.rowSelector));

  let page = 1;
  let size = config.defaultSize || 8;

  function getFiltered() {
    const q = searchEl ? searchEl.value.trim().toLowerCase() : '';
    return q ? rows.filter(r => r.textContent.toLowerCase().includes(q)) : rows.slice();
  }

  function buildPageList(cur, total) {
    const nums   = new Set([1, total, cur, cur - 1, cur + 1].filter(n => n >= 1 && n <= total));
    const sorted = [...nums].sort((a, b) => a - b);
    const out = []; let prev = 0;
    for (const n of sorted) {
      if (n - prev > 1) out.push('…');
      out.push(n);
      prev = n;
    }
    return out;
  }

  function render() {
    const filtered   = getFiltered();
    const totalPages = Math.max(1, Math.ceil(filtered.length / size));
    if (page > totalPages) page = totalPages;

    const start = (page - 1) * size;
    rows.forEach(r => (r.style.display = 'none'));
    filtered.slice(start, start + size).forEach(r => (r.style.display = ''));

    // empty state
    const tbody = rows[0]?.closest('tbody');
    if (tbody) {
      const existing = tbody.querySelector('.tc-empty-row');
      if (existing) existing.remove();
      if (filtered.length === 0) {
        const colspan = tbody.closest('table')?.querySelectorAll('thead th').length || 1;
        const tr = document.createElement('tr');
        tr.className = 'tc-empty-row';
        tr.innerHTML = `<td colspan="${colspan}" class="text-center text-secondary py-4">No results found.</td>`;
        tbody.appendChild(tr);
      }
    }

    if (!paginEl) return;
    paginEl.innerHTML = '';
    const dropdownEl = document.querySelector('.clzst');
    const isDjangoEmpty = !!document.querySelector('.tc-django-empty');
    if (dropdownEl) dropdownEl.classList.toggle('impose-no-display', isDjangoEmpty);
    if (isDjangoEmpty || totalPages <= 1) return;
    buildPageList(page, totalPages).forEach(item => {
      const li = document.createElement('li');
      if (item === '…') {
        li.className = 'page-item disabled';
        li.innerHTML = '<a class="page-link">…</a>';
      } else {
        li.className = `page-item${item === page ? ' active' : ''}`;
        li.innerHTML = `<a class="page-link" style="cursor:pointer">${item}</a>`;
        li.querySelector('a').addEventListener('click', () => { page = item; render(); });
      }
      paginEl.appendChild(li);
    });
  }

  // expose setPageSize to dropdown onclick — uses the fn name you pass in
  window[config.setFnName || 'setPageSize'] = function (n) {
    size = n; page = 1;
    if (pageEl) pageEl.textContent = n;
    render();
  };

  if (searchEl) searchEl.addEventListener('input', () => { page = 1; render(); });

  window[config.reindexFnName || ('reindex_' + (config.setFnName || 'setPageSize'))] = function () {
    rows = Array.from(document.querySelectorAll(config.rowSelector));
    page = 1;
    render();
  };

  render();
}