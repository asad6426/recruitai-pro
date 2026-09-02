# RecruitAI Pro — Frontend

A static, responsive frontend for an AI-powered ATS / HR management product, built
from the design mockups in the parent folder using **HTML, CSS and Bootstrap 5.3**.

No build step, no backend — open a file and it runs.

---

## Running it

Open `index.html` in a browser, or serve the folder so relative paths behave exactly
like production:

```bash
cd recruitai-pro
python -m http.server 8080
# then visit http://localhost:8080
```

Bootstrap, Bootstrap Icons and the Inter font load from a CDN, so the pages need an
internet connection to render with their intended styling. Everything else — CSS, JS,
avatars, logos — is local.

---

## Pages

### Public
| File | Screen |
|---|---|
| `index.html` | Marketing landing page |
| `login.html` | Sign in (split brand/form layout) |
| `signup.html` | Create an account |
| `forgot-password.html` | Password reset request |
| `role-select.html` | "Tell us about yourself" — routes to a persona |

### Recruiter (`recruiter/`)
| File | Screen |
|---|---|
| `dashboard.html` | KPIs, recent applications, hiring funnel, interviews today, goal card |
| `candidates.html` | Filterable candidate table with a right-hand detail drawer |
| `candidate-profile.html` | Profile with Overview / Experience / Skills / Notes tabs |
| `resume-analysis.html` | AI match donut, score breakdown, skills comparison, suggestions |
| `jobs.html` | Job postings table |
| `post-job.html` | New job posting form |

### Applicant (`applicant/`)
| File | Screen |
|---|---|
| `dashboard.html` | Resume score, applications, profile completion, recommendations |
| `browse-jobs.html` | Job search with working filters and sorting |
| `job-details.html` | Full job posting with match breakdown and apply modal |

Sidebar items that have no page yet (Interviews, Analytics, Notifications, Settings,
My Applications, Skill Insights) render in a muted **Soon** state rather than linking
nowhere.

---

## Structure

```
recruitai-pro/
├── index.html · login.html · signup.html · forgot-password.html · role-select.html
├── recruiter/   6 pages
├── applicant/   3 pages
└── assets/
    ├── css/
    │   ├── theme.css        design tokens, Bootstrap overrides, dark theme
    │   ├── layout.css       app shell, sidebar, topbar, auth shell, footer
    │   └── components.css   cards, tables, badges, donuts, funnel, timeline, drawer
    ├── js/
    │   ├── app.js           theme toggle, sidebar, animations, search modal, toasts
    │   ├── candidates.js    candidate table filtering, sorting, detail drawer
    │   └── jobs.js          job search filters, sorting, save toggle
    └── img/                 logo + SVG avatars
```

### Styling

All colour, spacing and radius values are CSS custom properties defined once in
`assets/css/theme.css`, which also overrides Bootstrap's own variables
(`--bs-primary`, `--bs-body-bg`, …). To rebrand, edit the tokens at the top of that
file — nothing downstream hard-codes a colour.

Dark mode remaps the same tokens under `[data-bs-theme="dark"]`, so both themes stay
in sync automatically.

---

## Interactive features

- **Dark / light theme** toggle in every topbar, persisted to `localStorage`.
- **Responsive sidebar** — collapses to a slide-in panel below 992px.
- **Candidate table** — live search, role filter, ATS score threshold, column sorting,
  select-all, and a detail drawer that fills from the clicked row.
- **Job search** — keyword, location, job type, remote/hybrid, salary floor, sorting,
  save-job toggle, live result count.
- **Animated charts** — donuts, progress meters and funnel bars grow from zero when
  scrolled into view; KPI numbers count up.
- **Command palette** — `Ctrl`/`⌘` + `K` opens a searchable quick-jump modal.
- **Forms** — Bootstrap validation on login, signup, reset, post-job and apply.
- **Toasts** for shortlist, reject, save, export and other actions.

Reduced-motion preferences are respected: all animations collapse to instant.

---

## Notes

This is a frontend prototype. There is no server, no database and no authentication —
form submissions show a toast and, where it makes sense, navigate to the next screen.
All candidate, job and score data is static markup taken from the source designs.
