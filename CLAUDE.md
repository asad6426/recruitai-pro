# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

- `*.jpeg` at the repo root — the original design mockup screenshots the UI was built from. Reference only; not part of the app.
- `problem/` — screenshots documenting bugs/gaps found in the live deployment. Reference only.
- `recruitai-pro/` — the static, no-build **prototype** for an AI-powered ATS / HR management product (HTML + CSS + Bootstrap 5.3 + vanilla JS), built straight from the mockups. It is frozen and intentionally not wired to `backend/` — all data in it is hardcoded markup, not a thing to keep in sync.
- `backend/` — a Django project that is the **real, working application**: full data model plus the views/forms/URLs/templates that serve it (`backend/portal/`). This is not schema-only — see `backend/README.md` for the app layout and design decisions (why `Application` rather than `Candidate` holds ATS score/stage, why `ResumeAnalysis` is per resume+job pair, etc.), and the root [`README.md`](README.md) for the full feature list.

There are effectively **two frontends**: the frozen static prototype in `recruitai-pro/`, and a second, independent server-rendered UI in `backend/templates/` (styled by `backend/portal/static/`, a forked copy of `recruitai-pro/assets/`) that is driven by real views and a real database. They share a visual language but are not the same code — a fix in one does not apply to the other.

## Commands (frontend)

There is no build step, package manager, or test suite for the frontend — it's plain HTML/CSS/JS served as static files.

Run it locally from `recruitai-pro/`:
```bash
cd recruitai-pro
python -m http.server 8080
# visit http://localhost:8080
```
Opening the HTML files directly in a browser also works. Bootstrap, Bootstrap Icons, and the Inter font load from a CDN, so an internet connection is needed for correct styling; everything else (CSS, JS, images) is local.

## Commands (backend)

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # then browse/create data at /admin/
python manage.py runserver
```

Run `python manage.py makemigrations <app>` after changing any model in
`backend/*/models.py`, then `migrate` again.

## Architecture — `recruitai-pro/` (static prototype)

**This frontend has no backend wired in.** The pages in `recruitai-pro/` are still fully static — form submissions validate client-side, show a toast, and (where relevant) navigate to a static next page, and all candidate/job/score data in the markup is hardcoded from the source designs. Nothing in `recruitai-pro/` calls `backend/` — there's no API layer, no fetch calls, no auth wiring between the two, and none is planned; it stays frozen as a design reference.

**Pages** are plain HTML files, each self-contained and loading the same CSS/JS bundle via relative paths:
- Public: `index.html`, `login.html`, `signup.html`, `forgot-password.html`, `role-select.html`
- `recruiter/`: `dashboard.html`, `candidates.html`, `candidate-profile.html`, `resume-analysis.html`, `jobs.html`, `post-job.html`
- `applicant/`: `dashboard.html`, `browse-jobs.html`, `job-details.html`

Sidebar nav items with no page *in this prototype* (Interviews, Analytics, Notifications, Settings, My Applications, Skill Insights) are intentionally rendered in a muted "Soon" state (`is-soon` class, `href="#"`) rather than linking nowhere — follow this pattern here instead of adding a dead link when scaffolding a new nav item ahead of its page. This only applies to `recruitai-pro/`: the equivalent pages in `backend/` are real and built out (see below) — do not reintroduce "Soon" stubs there.

**CSS** (`assets/css/`), loaded in this order on every page — `theme.css` then `layout.css` then `components.css`:
- `theme.css` — all design tokens (color, spacing, radius) as CSS custom properties, plus Bootstrap variable overrides (`--bs-primary`, `--bs-body-bg`, etc.) and the `[data-bs-theme="dark"]` remap of the same tokens. To rebrand or retheme, edit tokens here only — nothing downstream hardcodes a color, and dark mode stays in sync automatically because it reuses the same token names.
- `layout.css` — app shell: sidebar, topbar, auth shell, footer.
- `components.css` — cards, tables, badges, donuts, funnel bars, timeline, drawer.

**JS** (`assets/js/`), all vanilla (IIFEs, no framework, no bundler):
- `app.js` — loaded on every page; owns theme toggle (persisted to `localStorage` under `ra-theme`), responsive sidebar, scroll-triggered animation of meters/donuts/funnel bars (`IntersectionObserver`, driven by `data-value`/`data-height` attributes on elements already present at threshold 0.25/0.4), count-up numbers (`[data-count]`), the `Ctrl/Cmd+K` command palette, the toast system, tooltips, and generic Bootstrap form-validation wiring. Exposes `window.RA.toast(message, variant)` for page-level scripts to reuse.
- `candidates.js` — powers `recruiter/candidates.html` only: table search/role/score filtering and column sorting operate on `data-*` attributes on each `<tr>`, plus select-all and the right-hand detail drawer (filled from the clicked row's `data-*` attributes, not a separate data source).
- `jobs.js` — powers `applicant/browse-jobs.html` only: keyword/location/type/remote/salary filtering, sorting, and save-job toggle, same `data-*`-attribute-on-row pattern.

When adding interactivity to a specific page, follow the existing pattern: read state out of `data-*` attributes already in the static markup rather than introducing a JS data model, and put shared behavior in `app.js` vs. page-specific behavior in its own file.

**Declarative hooks used throughout the markup** (wired up by `app.js`): `data-ra-theme-toggle`, `data-ra-sidebar-toggle`, `data-ra-search-open` / `data-ra-search-input`, `data-ra-toast="message"` (+ `data-ra-toast-variant`), `data-ra-password-toggle="<input id>"`, and `.needs-validation` forms with `data-ra-success` / `data-ra-next` for post-submit toast + redirect. Reuse these instead of writing bespoke event handlers when a new element needs the same behavior.

Reduced-motion preferences are respected: animations collapse to instant rather than being skipped separately.

## Architecture — `backend/` (the real application)

`backend/portal/` is where the actual app lives — not just data models. It's split by
role/purpose rather than one `views.py`:
- `views_marketing.py` — the public landing page.
- `views_auth.py` — signup, role-select, login-redirect (Django's built-in
  `LoginView`/`LogoutView`/password-reset views are wired directly in `urls.py`).
- `views_recruiter.py` / `views_applicant.py` — one file per role, each with its own
  `_org(request)` / `_candidate(request)` helper to scope queries to the logged-in
  user's organization or profile. Every view is gated with `@role_required("recruiter")`
  or `@role_required("applicant")` from `decorators.py`, which redirects role-less users
  to `role_select` and wrong-role users to their own dashboard rather than 403ing.
- `services.py` — all computed values that don't map 1:1 to a model field (match %,
  resume score, funnel percentages, profile completion, notification triggers) as
  plain functions over real querysets. `run_resume_analysis()` is the deterministic,
  rule-based "AI" scorer — real computation, not an external API call.
- `forms.py` — plain `forms.Form` subclasses (not `ModelForm`) so field names can be
  hand-matched to the prototype's existing input `id`s/`name`s.
- `context_processors.py` — `search_quicklinks` (global-search modal data) and
  `notifications_context` (the unread-count badge on the bell icon) run on every
  request for logged-in users; both are registered in `config/settings.py`.

**Notifications**: the `notifications` app has one model, `Notification`
(`recipient`, `sender`, optional `application`, `verb`, `message`, `is_read`). Every
trigger goes through a `services.notify_*` helper called from the relevant view —
`notify_new_application` (apply → hiring manager or all org recruiters),
`notify_interview_scheduled`, `notify_stage_changed`, and the recruiter's
"Message Candidate" action creates a `Notification` directly with `verb="message"`.
Viewing the Notifications page marks everything unread as read; there is no per-item
read toggle. Add a new event type by adding a `Verb` choice + a `notify_*` helper, not
a new model.

**Templates** under `backend/templates/` mirror the role split: `auth/`, `marketing/`,
`recruiter/` (with `base_recruiter.html` + `_sidebar.html`), `applicant/` (with
`base_applicant.html` + `_sidebar.html`), and `partials/` for shared bits (footer,
search modals, toast bridge). Every recruiter/applicant page extends its role's base
template and sets `active_nav` in the view context to highlight the current sidebar
item. Static assets live at `backend/portal/static/assets/` — a forked copy of
`recruitai-pro/assets/`, not a symlink, so a fix to one does not propagate to the
other.

When adding a new page to `backend/`: add the view (in the right `views_*.py`), add
the URL to `portal/urls.py`, add the template extending the correct base, and wire it
into that role's `_sidebar.html` (and top-nav in `base_applicant.html` if applicant-
facing) — do not leave it as an `is-soon` stub; that pattern is reserved for
`recruitai-pro/` only.
