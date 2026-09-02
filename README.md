# RecruitAI Pro — HR Management System

An AI-assisted ATS (Applicant Tracking System) product, built in two parallel layers:

1. **`recruitai-pro/`** — a static, no-build HTML/CSS/JS prototype built directly from the
   original design mockups (the `*.jpeg` files at the repo root). Every page here is
   self-contained; there is no server behind it and no real data — it exists to lock in
   the visual design.
2. **`backend/`** — a full Django application (models, views, templates, auth,
   file uploads, notifications) that implements the same product for real, backed by a
   database. This is the one that actually runs as a product.

The two are independent. `recruitai-pro/` never calls `backend/`, and `backend/` ships
its own copy of the templates/CSS/JS re-authored to be server-rendered from real data.
If you're looking for the working app, you want `backend/`.

---

## Repo layout

```
.
├── *.jpeg                     Original design mockups (reference only)
├── problem/                   Screenshots of bugs/gaps found in the live deployment
├── recruitai-pro/             Static frontend prototype (no backend, hardcoded data)
└── backend/                   Django project — the real, working application
    ├── accounts/              User, RecruiterProfile, ApplicantProfile, RecruiterGoal
    ├── organizations/         Organization (the company behind a job posting)
    ├── taxonomy/              Skill (shared vocabulary across jobs/candidates/resumes)
    ├── jobs/                  Job, JobSkill, JobRequirement, JobResponsibility, JobBenefit, SavedJob
    ├── candidates/            WorkExperience, Education, CandidateSkill, Certification
    ├── resumes/               Resume, ResumeAnalysis, ResumeSkillMatch, OptimizationSuggestion
    ├── applications/          Application (the pipeline entity), Note, Interview
    ├── notifications/         Notification (in-app notifications + recruiter→candidate messages)
    ├── portal/                All views, forms, URLs, templates, static assets — the app itself
    └── templates/             Server-rendered HTML (auth, marketing, recruiter/, applicant/)
```

---

## Running it

### Frontend prototype (`recruitai-pro/`)

No build step, no dependencies beyond a browser.

```bash
cd recruitai-pro
python -m http.server 8080
# visit http://localhost:8080
```

Bootstrap 5.3, Bootstrap Icons, and the Inter font load from a CDN — everything else
(CSS, JS, images) is local. This mode never talks to the Django backend.

### Backend (`backend/`) — the real application

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser        # for /admin/
python manage.py seed_demo              # optional: populate demo org/jobs/candidates
python manage.py runserver
# visit http://localhost:8000
```

`seed_demo` is safe to run once on a fresh database — it skips itself if demo data
(`InnovateTech` org) already exists. After migrating any model change, run
`python manage.py makemigrations <app>` before `migrate` again.

---

## What actually works (backend app)

Everything below is a real view + template + database round trip — not mocked markup.

### Everyone
- Sign up, log in, log out, role select (Recruiter vs Applicant)
- Password reset by email, password change from Settings
- Profile edit (name, avatar, and role-specific fields) — recruiter avatar/top-nav
  "Profile" link both go here
- Global search (quick-jump to recent candidates/jobs), theme toggle (dark/light)
- Notifications inbox with an unread-count badge on the bell icon and sidebar item

### Recruiter
- Dashboard — live KPIs, recent applications, hiring funnel, today's interviews, hiring
  goal progress
- Candidates — filterable/sortable table across the whole org's applicant pool
- Candidate profile — experience, skills, certifications, notes thread, resume link,
  reject/shortlist, **schedule an interview**, **send an individual message to the
  candidate**
- Resume analysis — AI-style match score breakdown, skill gap comparison, optimization
  suggestions, link to the actual uploaded resume file
- Jobs — list, post new (multi-section form: role details, requirements, screening
  rules, publish targets), edit, pause/close, delete drafts
- **Interviews** — org-wide upcoming/past interview list
- **Analytics** — application volume + trend, pipeline-by-stage breakdown, source
  breakdown, top jobs by applicant volume, avg time-to-hire
- **Settings** — change password

### Applicant
- Dashboard — resume score, profile completion, recommended jobs, recent applications,
  recent activity feed
- Browse jobs — keyword/location filters, per-job match %, save/unsave
- Job details — skill match breakdown, apply flow (pick a resume, add a note, consent)
- Resume upload, with the uploaded file actually openable afterward (by both the
  applicant and the recruiter reviewing them — this used to be a dead end)
- **My Applications** — full history of every job applied to, filterable by stage
- **Interviews** — everything scheduled by recruiters, upcoming and past
- **Skill Insights** — proficiency bars for your skills, plus a ranked list of skills
  worth adding based on recurring gaps across resume analyses
- **Settings** — change password

### Notifications, specifically
A small `notifications` app backs all of this:
- Applying to a job notifies the job's hiring manager (or every recruiter at the org,
  if none is set).
- Scheduling an interview notifies the candidate.
- Changing an application's stage notifies the candidate.
- A recruiter can message any one candidate directly from their profile page; it
  arrives as a notification, not an email.

There's no email/push delivery — notifications are in-app only, read via the bell icon
or the Notifications page, and marked read the moment that page is opened.

---

## Design decisions worth knowing

- **`Application` is the pipeline entity, not `Candidate`.** ATS score, match %, and
  pipeline stage all belong to one candidate's application to one specific job —
  `ApplicantProfile` is the reusable person, `Application` is the per-job state.
- **`ResumeAnalysis` is per (resume, job) pair**, not per resume — score and skill
  breakdown are always relative to one job's requirements.
- **Skills are normalized** into a single `Skill` table, joined through `JobSkill`,
  `CandidateSkill`, and `ResumeSkillMatch` rather than duplicated as free text.
- **Resume/ATS scoring is deterministic, not a real AI/LLM call.** `portal/services.py`
  computes match % from real `CandidateSkill` / `JobSkill` / `WorkExperience` overlap —
  same idea as an AI screener, implemented as plain rules so the whole thing runs with
  no external API key or cost.
- Money/percent/day fields (salary, ATS score, match %) are stored as plain integers,
  not derived at render time — the backend is the source of truth for these numbers.

## Known gaps

- No real-time delivery (no websockets/polling) — notifications and dashboards update
  on page load/refresh, not live.
- No email delivery for notifications (only Django's built-in password-reset email).
- "Join Meeting" and "View Calendar" on the recruiter dashboard are still placeholders
  — there's no real video-call or calendar integration behind them.
- `recruitai-pro/` (the static prototype) is intentionally frozen and not wired to the
  backend — treat it as a design reference, not a thing to keep in sync.
