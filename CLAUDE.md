# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

- `*.jpeg` at the repo root — the original design mockup screenshots the UI was built from. Reference only; not part of the app.
- `recruitai-pro/` — the static, no-build frontend for an AI-powered ATS / HR management product (HTML + CSS + Bootstrap 5.3 + vanilla JS). All frontend work happens inside this folder.
- `backend/` — a Django project holding the database schema that backs the frontend (models only — no views/APIs wired up yet). See `backend/README.md` for the app layout and design decisions (why `Application` rather than `Candidate` holds ATS score/stage, why `ResumeAnalysis` is per resume+job pair, etc.).

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

## Architecture

**Frontend has no backend wired in.** The pages in `recruitai-pro/` are still fully static — form submissions validate client-side, show a toast, and (where relevant) navigate to a static next page, and all candidate/job/score data in the markup is hardcoded from the source designs. `backend/` defines the Django data model these pages *would* be backed by, but nothing in `recruitai-pro/` calls it yet — there's no API layer, no fetch calls, no auth wiring between the two.

**Pages** are plain HTML files, each self-contained and loading the same CSS/JS bundle via relative paths:
- Public: `index.html`, `login.html`, `signup.html`, `forgot-password.html`, `role-select.html`
- `recruiter/`: `dashboard.html`, `candidates.html`, `candidate-profile.html`, `resume-analysis.html`, `jobs.html`, `post-job.html`
- `applicant/`: `dashboard.html`, `browse-jobs.html`, `job-details.html`

Sidebar nav items with no page yet (Interviews, Analytics, Notifications, Settings, My Applications, Skill Insights) are intentionally rendered in a muted "Soon" state (`is-soon` class, `href="#"`) rather than linking nowhere — follow this pattern instead of adding a dead link when scaffolding a new nav item ahead of its page.

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
