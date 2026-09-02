/* ==========================================================================
   RecruitAI Pro — app.js
   Shared behaviour for every page: theme toggle, mobile sidebar, animated
   meters/donuts/counters, command palette, toasts, tooltips.
   ========================================================================== */
(function () {
  'use strict';

  var THEME_KEY = 'ra-theme';

  /* ---------------------------------------------------------------- theme */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    document.querySelectorAll('[data-ra-theme-icon]').forEach(function (icon) {
      icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
    });
  }

  function initTheme() {
    var stored = null;
    try { stored = localStorage.getItem(THEME_KEY); } catch (e) { /* private mode */ }
    applyTheme(stored || 'light');

    document.querySelectorAll('[data-ra-theme-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var next = document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* ignore */ }
      });
    });
  }

  /* -------------------------------------------------------------- sidebar */
  function initSidebar() {
    var sidebar = document.querySelector('.ra-sidebar');
    if (!sidebar) return;

    var backdrop = document.querySelector('.ra-sidebar-backdrop');

    function close() {
      sidebar.classList.remove('is-open');
      if (backdrop) backdrop.classList.remove('is-open');
    }

    document.querySelectorAll('[data-ra-sidebar-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        sidebar.classList.toggle('is-open');
        if (backdrop) backdrop.classList.toggle('is-open', sidebar.classList.contains('is-open'));
      });
    });

    if (backdrop) backdrop.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  }

  /* ------------------------------------------------- animate on first view
     Meters, score bars, donut rings and funnel columns all start at zero and
     grow to their data-* target the first time they scroll into view.        */
  function animate(el) {
    if (el.dataset.raAnimated === '1') return;
    el.dataset.raAnimated = '1';

    if (el.classList.contains('ra-meter__fill') || el.classList.contains('ra-score__fill')) {
      el.style.width = (el.dataset.value || 0) + '%';
    } else if (el.classList.contains('ra-donut__value')) {
      var r = parseFloat(el.getAttribute('r'));
      var circumference = 2 * Math.PI * r;
      var pct = Math.max(0, Math.min(100, parseFloat(el.dataset.value || 0)));
      el.style.strokeDasharray = circumference;
      el.style.strokeDashoffset = circumference * (1 - pct / 100);
    } else if (el.classList.contains('ra-funnel__bar')) {
      el.style.height = (el.dataset.height || 0) + '%';
    }
  }

  function initAnimatedBars() {
    var targets = document.querySelectorAll('.ra-meter__fill, .ra-score__fill, .ra-donut__value, .ra-funnel__bar');
    if (!targets.length) return;

    // Donuts need their dash array set up before they are ever painted.
    document.querySelectorAll('.ra-donut__value').forEach(function (ring) {
      var c = 2 * Math.PI * parseFloat(ring.getAttribute('r'));
      ring.style.strokeDasharray = c;
      ring.style.strokeDashoffset = c;
    });

    if (!('IntersectionObserver' in window)) {
      targets.forEach(animate);
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          animate(entry.target);
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.25 });

    targets.forEach(function (t) { io.observe(t); });

    // Panes hidden behind a tab are never "intersecting", so animate them the
    // moment their tab is shown.
    document.addEventListener('shown.bs.tab', function (e) {
      var pane = document.querySelector(e.target.dataset.bsTarget);
      if (!pane) return;
      pane.querySelectorAll('.ra-meter__fill, .ra-score__fill, .ra-donut__value, .ra-funnel__bar').forEach(animate);
    });
  }

  /* ------------------------------------------------------- count-up values */
  function countUp(el) {
    var target = parseFloat(el.dataset.count);
    if (isNaN(target)) return;

    var decimals = (el.dataset.decimals ? parseInt(el.dataset.decimals, 10) : 0);
    var prefix = el.dataset.prefix || '';
    var suffix = el.dataset.suffix || '';
    var duration = 900;
    var start = null;

    function frame(ts) {
      if (start === null) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      var value = target * eased;
      el.textContent = prefix + value.toLocaleString('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      }) + suffix;
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function initCounters() {
    var els = document.querySelectorAll('[data-count]');
    if (!els.length) return;

    if (!('IntersectionObserver' in window)) {
      els.forEach(countUp);
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          countUp(entry.target);
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.4 });

    els.forEach(function (el) { io.observe(el); });
  }

  /* ------------------------------------------------------- command palette */
  function initSearchModal() {
    var modalEl = document.getElementById('globalSearchModal');
    if (!modalEl || !window.bootstrap) return;

    var modal = new bootstrap.Modal(modalEl);

    document.querySelectorAll('[data-ra-search-open]').forEach(function (el) {
      el.addEventListener('click', function (e) { e.preventDefault(); modal.show(); });
      el.addEventListener('focus', function () { el.blur(); modal.show(); });
    });

    document.addEventListener('keydown', function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        modal.show();
      }
    });

    modalEl.addEventListener('shown.bs.modal', function () {
      var input = modalEl.querySelector('input');
      if (input) input.focus();
    });

    // Filter the static result list as you type.
    var input = modalEl.querySelector('[data-ra-search-input]');
    if (input) {
      input.addEventListener('input', function () {
        var q = input.value.trim().toLowerCase();
        var shown = 0;
        modalEl.querySelectorAll('[data-ra-search-item]').forEach(function (item) {
          var hit = !q || item.textContent.toLowerCase().indexOf(q) !== -1;
          item.classList.toggle('d-none', !hit);
          if (hit) shown++;
        });
        var empty = modalEl.querySelector('[data-ra-search-empty]');
        if (empty) empty.classList.toggle('d-none', shown > 0);
      });
    }
  }

  /* ---------------------------------------------------------------- toasts */
  function toast(message, variant) {
    var stack = document.querySelector('.ra-toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'ra-toast-stack';
      document.body.appendChild(stack);
    }

    var icons = { success: 'bi-check-circle-fill', danger: 'bi-x-circle-fill', info: 'bi-info-circle-fill' };
    var kind = variant || 'success';

    var el = document.createElement('div');
    el.className = 'toast align-items-center border-0 shadow';
    el.setAttribute('role', 'status');
    el.innerHTML =
      '<div class="d-flex">' +
        '<div class="toast-body d-flex align-items-center gap-2">' +
          '<i class="bi ' + (icons[kind] || icons.info) + ' text-' + (kind === 'danger' ? 'danger' : kind === 'info' ? 'primary' : 'success') + '"></i>' +
          '<span>' + message + '</span>' +
        '</div>' +
        '<button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
      '</div>';
    stack.appendChild(el);

    if (window.bootstrap) {
      var t = new bootstrap.Toast(el, { delay: 3200 });
      t.show();
      el.addEventListener('hidden.bs.toast', function () { el.remove(); });
    } else {
      setTimeout(function () { el.remove(); }, 3200);
    }
  }

  /* Any element with data-ra-toast="message" fires a toast when clicked. */
  function initToastTriggers() {
    document.addEventListener('click', function (e) {
      var trigger = e.target.closest('[data-ra-toast]');
      if (!trigger) return;
      if (trigger.tagName === 'A' && trigger.getAttribute('href') === '#') e.preventDefault();
      toast(trigger.dataset.raToast, trigger.dataset.raToastVariant);
    });
  }

  /* ------------------------------------------------------------- tooltips */
  function initTooltips() {
    if (!window.bootstrap) return;
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
      new bootstrap.Tooltip(el);
    });
  }

  /* ---------------------------------------------------- bootstrap forms
     A form that has a real `action` attribute submits for real to Django on
     valid input — only the invalid branch is intercepted (HTML5 validation
     UI). A form with no `action` (none should remain, but kept as a safety
     net) falls back to the old fully-client-side toast/redirect fakery. */
  function initFormValidation() {
    document.querySelectorAll('.needs-validation').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
          form.classList.add('was-validated');
          return;
        }
        form.classList.add('was-validated');

        if (form.hasAttribute('action')) return; // let it really submit

        e.preventDefault();
        var modalEl = form.closest('.modal');
        if (modalEl && window.bootstrap) {
          var instance = bootstrap.Modal.getInstance(modalEl);
          if (instance) instance.hide();
        }

        var msg = form.dataset.raSuccess;
        if (msg) toast(msg, 'success');
        var next = form.dataset.raNext;
        if (next) setTimeout(function () { window.location.href = next; }, 700);
      });
    });
  }

  /* ------------------------------------------------------------- csrf */
  function getCookie(name) {
    var match = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return match ? decodeURIComponent(match.pop()) : '';
  }

  /* ------------------------------------------------------- password reveal */
  function initPasswordToggles() {
    document.querySelectorAll('[data-ra-password-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var input = document.getElementById(btn.dataset.raPasswordToggle);
        if (!input) return;
        var reveal = input.type === 'password';
        input.type = reveal ? 'text' : 'password';
        var icon = btn.querySelector('i');
        if (icon) icon.className = reveal ? 'bi bi-eye-slash' : 'bi bi-eye';
        btn.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
      });
    });
  }

  /* ----------------------------------------------- save-job (bookmark) toggle
     Shared by browse-jobs.html cards and job-details.html — both render
     `.ra-save-btn[data-save-url]`; this POSTs to that URL and applies
     whatever { saved: true|false } comes back. */
  function initSaveToggle() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.ra-save-btn');
      if (!btn || !btn.dataset.saveUrl) return;
      e.preventDefault();

      fetch(btn.dataset.saveUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          btn.classList.toggle('is-saved', data.saved);
          var icon = btn.querySelector('i');
          if (icon) icon.className = data.saved ? 'bi bi-bookmark-fill' : 'bi bi-bookmark';
          toast(data.saved ? 'Job saved to your list.' : 'Job removed from saved.', data.saved ? 'success' : 'info');
        })
        .catch(function () { toast('Could not update saved jobs.', 'danger'); });
    });
  }

  /* ------------------------------------------- optimization-suggestion toggle
     resume-analysis.html suggestion checkboxes: `input[data-toggle-url]`. */
  function initSuggestionToggle() {
    document.querySelectorAll('input[type="checkbox"][data-toggle-url]').forEach(function (box) {
      box.addEventListener('change', function () {
        fetch(box.dataset.toggleUrl, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' }
        }).catch(function () { toast('Could not save that.', 'danger'); });
      });
    });
  }

  /* ------------------------------------------------------------------ init */
  document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    initPasswordToggles();
    initSidebar();
    initAnimatedBars();
    initCounters();
    initSearchModal();
    initToastTriggers();
    initTooltips();
    initFormValidation();
    initSaveToggle();
    initSuggestionToggle();
  });

  // Expose for page-level scripts.
  window.RA = { toast: toast, getCookie: getCookie };
})();
