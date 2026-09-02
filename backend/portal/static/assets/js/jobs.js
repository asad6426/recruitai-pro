/* ==========================================================================
   RecruitAI Pro — jobs.js
   Browse Jobs: keyword/location search, job-type + remote filters, salary
   floor, sorting, save-job toggle and the live result counter.
   ========================================================================== */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var list = document.getElementById('jobList');
    if (!list) return;

    var cards = Array.prototype.slice.call(list.querySelectorAll('[data-job]'));
    var countLabel = document.getElementById('jobCount');
    var empty = document.getElementById('jobEmpty');
    var keyword = document.getElementById('jobKeyword');
    var location = document.getElementById('jobLocation');
    var salaryRange = document.getElementById('salaryRange');
    var salaryOut = document.getElementById('salaryOut');
    var sortSelect = document.getElementById('jobSort');
    var typeBoxes = Array.prototype.slice.call(document.querySelectorAll('.job-type-filter'));
    var remoteRadios = Array.prototype.slice.call(document.querySelectorAll('input[name="remoteFilter"]'));

    function selectedTypes() {
      return typeBoxes.filter(function (b) { return b.checked; }).map(function (b) { return b.value; });
    }

    function selectedRemote() {
      var hit = remoteRadios.filter(function (r) { return r.checked; })[0];
      return hit ? hit.value : 'any';
    }

    function applyFilters() {
      var q = (keyword && keyword.value.trim().toLowerCase()) || '';
      var loc = (location && location.value.trim().toLowerCase()) || '';
      var types = selectedTypes();
      var remote = selectedRemote();
      var minSalary = parseInt((salaryRange && salaryRange.value) || '0', 10);
      var visible = 0;

      cards.forEach(function (card) {
        var text = (card.dataset.title + ' ' + card.dataset.company + ' ' + card.dataset.skills).toLowerCase();
        var matchesText = !q || text.indexOf(q) !== -1;
        var matchesLoc = !loc || card.dataset.location.toLowerCase().indexOf(loc) !== -1;
        var matchesType = !types.length || types.indexOf(card.dataset.type) !== -1;
        var matchesRemote = remote === 'any' || card.dataset.remote === remote;
        var matchesSalary = parseInt(card.dataset.salaryMax, 10) >= minSalary;
        var show = matchesText && matchesLoc && matchesType && matchesRemote && matchesSalary;

        card.classList.toggle('d-none', !show);
        if (show) visible++;
      });

      if (countLabel) countLabel.textContent = visible;
      if (empty) empty.classList.toggle('d-none', visible > 0);
    }

    function applySort() {
      if (!sortSelect) return;
      var mode = sortSelect.value;

      var sorted = cards.slice().sort(function (a, b) {
        if (mode === 'salary') return parseInt(b.dataset.salaryMax, 10) - parseInt(a.dataset.salaryMax, 10);
        if (mode === 'recent') return parseInt(a.dataset.posted, 10) - parseInt(b.dataset.posted, 10);
        return parseInt(b.dataset.match, 10) - parseInt(a.dataset.match, 10);   // most relevant
      });

      sorted.forEach(function (card) { list.appendChild(card); });
      if (empty) list.appendChild(empty);
    }

    [keyword, location].forEach(function (el) {
      if (el) el.addEventListener('input', applyFilters);
    });
    typeBoxes.concat(remoteRadios).forEach(function (el) {
      el.addEventListener('change', applyFilters);
    });

    if (salaryRange) {
      salaryRange.addEventListener('input', function () {
        if (salaryOut) salaryOut.textContent = '$' + salaryRange.value + 'k';
        applyFilters();
      });
    }

    if (sortSelect) sortSelect.addEventListener('change', applySort);

    var resetBtn = document.getElementById('resetFilters');
    if (resetBtn) {
      resetBtn.addEventListener('click', function (e) {
        e.preventDefault();
        typeBoxes.forEach(function (b) { b.checked = b.value === 'full-time'; });
        remoteRadios.forEach(function (r) { r.checked = r.value === 'any'; });
        if (salaryRange) salaryRange.value = salaryRange.min;
        if (salaryOut) salaryOut.textContent = '$' + salaryRange.min + 'k';
        if (keyword) keyword.value = '';
        if (location) location.value = '';
        applyFilters();
      });
    }

    var searchForm = document.getElementById('jobSearchForm');
    if (searchForm) {
      searchForm.addEventListener('submit', function (e) { e.preventDefault(); applyFilters(); });
    }

    // Save-toggle (bookmark) is handled globally by app.js's initSaveToggle(),
    // shared with job-details.html.

    applyFilters();
  });
})();
