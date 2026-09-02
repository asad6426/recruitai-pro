/* ==========================================================================
   RecruitAI Pro — candidates.js
   Candidate table: search, role filter, ATS threshold, sorting, select-all,
   and the right-hand detail drawer.
   ========================================================================== */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var table = document.getElementById('candidateTable');
    if (!table) return;

    var tbody = table.querySelector('tbody');
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
    var searchInput = document.getElementById('candidateSearch');
    var roleSelect = document.getElementById('roleFilter');
    var scoreSelect = document.getElementById('scoreFilter');
    var countLabel = document.getElementById('candidateCount');
    var emptyRow = document.getElementById('candidateEmpty');
    var selectAll = document.getElementById('selectAllCandidates');

    /* ------------------------------------------------------------ filtering */
    function applyFilters() {
      var q = (searchInput && searchInput.value.trim().toLowerCase()) || '';
      var role = (roleSelect && roleSelect.value) || 'all';
      var minScore = parseInt((scoreSelect && scoreSelect.value) || '0', 10);
      var visible = 0;

      rows.forEach(function (row) {
        var haystack = (row.dataset.name + ' ' + row.dataset.email + ' ' + row.dataset.role).toLowerCase();
        var matchesText = !q || haystack.indexOf(q) !== -1;
        var matchesRole = role === 'all' || row.dataset.roleKey === role;
        var matchesScore = parseInt(row.dataset.score, 10) >= minScore;
        var show = matchesText && matchesRole && matchesScore;

        row.classList.toggle('d-none', !show);
        if (show) visible++;
      });

      if (countLabel) countLabel.textContent = visible;
      if (emptyRow) emptyRow.classList.toggle('d-none', visible > 0);
    }

    if (searchInput) searchInput.addEventListener('input', applyFilters);
    if (roleSelect) roleSelect.addEventListener('change', applyFilters);
    if (scoreSelect) scoreSelect.addEventListener('change', applyFilters);

    /* -------------------------------------------------------------- sorting */
    table.querySelectorAll('th.is-sortable').forEach(function (th) {
      th.addEventListener('click', function () {
        var key = th.dataset.sortKey;
        var dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';

        table.querySelectorAll('th.is-sortable').forEach(function (other) {
          if (other !== th) other.removeAttribute('data-dir');
        });
        th.dataset.dir = dir;

        var sorted = rows.slice().sort(function (a, b) {
          var av = a.dataset[key];
          var bv = b.dataset[key];
          var an = parseFloat(av);
          var bn = parseFloat(bv);
          var res = (!isNaN(an) && !isNaN(bn)) ? an - bn : String(av).localeCompare(String(bv));
          return dir === 'asc' ? res : -res;
        });

        sorted.forEach(function (row) { tbody.appendChild(row); });
        if (emptyRow) tbody.appendChild(emptyRow);
      });
    });

    /* ---------------------------------------------------------- select all */
    if (selectAll) {
      selectAll.addEventListener('change', function () {
        rows.forEach(function (row) {
          if (row.classList.contains('d-none')) return;
          var cb = row.querySelector('.row-check');
          if (cb) {
            cb.checked = selectAll.checked;
            row.classList.toggle('is-selected', selectAll.checked);
          }
        });
      });
    }

    tbody.addEventListener('change', function (e) {
      var cb = e.target.closest('.row-check');
      if (!cb) return;
      cb.closest('tr').classList.toggle('is-selected', cb.checked);
    });

    /* ------------------------------------------------------------- drawer */
    var drawer = document.getElementById('candidateDrawer');

    function fill(selector, value) {
      if (value === undefined) return;
      var el = drawer.querySelector(selector);
      if (el) el.textContent = value;
    }

    function openDrawer(row) {
      if (!drawer) return;

      fill('[data-drawer-name]', row.dataset.name);
      fill('[data-drawer-role]', row.dataset.role);
      fill('[data-drawer-location]', row.dataset.location);
      fill('[data-drawer-work]', row.dataset.work);
      fill('[data-drawer-score]', row.dataset.score);
      fill('[data-drawer-match]', row.dataset.match + '%');
      fill('[data-drawer-insight]', row.dataset.insight);

      var avatar = drawer.querySelector('[data-drawer-avatar]');
      if (avatar) {
        avatar.src = row.dataset.avatar;
        avatar.alt = row.dataset.name;
      }

      var skillWrap = drawer.querySelector('[data-drawer-skills]');
      if (skillWrap) {
        skillWrap.innerHTML = '';
        (row.dataset.skills || '').split('|').filter(Boolean).forEach(function (skill, i) {
          var chip = document.createElement('span');
          // First three skills are the confirmed matches in the design.
          chip.className = 'ra-chip ' + (i < 3 ? 'ra-chip--success' : '');
          chip.innerHTML = (i < 3 ? '<i class="bi bi-check-circle"></i>' : '') + skill;
          skillWrap.appendChild(chip);
        });
      }

      rows.forEach(function (r) { r.classList.remove('is-active'); });
      row.classList.add('is-active');
      drawer.classList.add('is-open');
    }

    tbody.addEventListener('click', function (e) {
      if (e.target.closest('.row-check') || e.target.closest('.dropdown')) return;
      var row = e.target.closest('tr[data-name]');
      if (row) openDrawer(row);
    });

    var closeBtn = drawer && drawer.querySelector('[data-drawer-close]');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () { drawer.classList.remove('is-open'); });
    }

    applyFilters();
  });
})();
