# RecruitAI Pro — Backend

The real, working application: a Django project with the full data model *and* the
views/templates/URLs that serve it — signup through applying for a job, recruiter
screening, interviews, notifications, the works. It was originally scaffolded as a
schema-only companion to the `recruitai-pro/` frontend prototype, but the `portal` app
below now implements the product for real, independent of that prototype.

See the root [`README.md`](../README.md) for the full feature list and how this
relates to `recruitai-pro/`.

## Run it

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo      # optional — demo org, jobs, candidates
python manage.py runserver
```

Then open `/` for the real app, or `/admin/` to browse and edit data directly through
Django admin (every model is registered).

## App layout

| App | Models | Backs |
|---|---|---|
| `accounts` | `User`, `RecruiterProfile`, `ApplicantProfile`, `RecruiterGoal` | login/signup/role-select, the logged-in identity in every page's topbar, the dashboard "Recruiter Goal" card |
| `organizations` | `Organization` | the company on a job posting / "About [Company]" card on job-details.html |
| `taxonomy` | `Skill` | shared skill vocabulary reused by jobs, candidates, and resume analysis |
| `jobs` | `Job`, `JobSkill`, `JobRequirement`, `JobResponsibility`, `JobBenefit`, `SavedJob` | post-job.html, jobs.html, browse-jobs.html, job-details.html |
| `candidates` | `WorkExperience`, `Education`, `CandidateSkill`, `Certification` | candidate-profile.html Overview/Experience/Skills tabs |
| `resumes` | `Resume`, `ResumeAnalysis`, `ResumeSkillMatch`, `OptimizationSuggestion` | resume-analysis.html |
| `applications` | `Application`, `Note`, `Interview` | candidates.html table + drawer, candidate-profile.html Notes tab, dashboard "Interviews Today", the Interviews list pages |
| `notifications` | `Notification` | the bell icon + Notifications page on both sides; new-application alerts, interview-scheduled alerts, stage-change alerts, and recruiter → candidate direct messages |
| `portal` | *(no models)* | every view, form, URL, and template — the app itself. Split into `views_marketing.py`, `views_auth.py`, `views_recruiter.py`, `views_applicant.py`, with shared computed-value logic in `services.py` |

`User.role` (`recruiter` / `applicant`) decides which of `RecruiterProfile` /
`ApplicantProfile` is attached — mirrors the `role-select.html` split.
`ApplicantProfile` **is** the "Candidate" entity the recruiter-side pages
refer to; there's no separate `Candidate` model.

## Key design decisions

- **`Application` is the pipeline entity**, not `Candidate`. A candidate's ATS
  score, match %, and stage are all specific to one job they applied to
  (`candidates.html` table rows are really `Application` rows joined to
  `ApplicantProfile` + `Job`). `Application.stage` choices follow the funnel
  order shown on the recruiter dashboard: `new_applied → screening → review →
  technical_test → interview → shortlisted → offer → hired`, plus `rejected`.
- **`ResumeAnalysis` is per (resume, job) pair**, not per resume — the AI
  match score, skill breakdown, and suggestions on resume-analysis.html are
  all specific to one job's requirements.
- **Skills are normalized** into one `Skill` table, joined through
  `JobSkill` (required + weight), `CandidateSkill` (category + proficiency),
  and `ResumeSkillMatch` (matched/partial/missing) — so the same skill name
  isn't duplicated as free text in three places.
- Money/percent/day fields (salary, ATS score, match %) are plain
  `PositiveInteger`/`PositiveSmallInteger` fields, not derived — the frontend
  displays them as-is rather than computing them client-side, so the backend
  is the source of truth.
- **Resume/ATS scoring (`services.run_resume_analysis`) is deterministic**, computed
  from real `CandidateSkill` vs `JobSkill` overlap and work-experience duration — not
  an external AI/LLM call. It reads as "AI insight" in the UI but costs nothing to run
  and needs no API key.
- **Notifications are a thin, generic model** (`recipient`, `sender`, optional
  `application`, `verb`, `message`) rather than one table per event type — every
  trigger (`services.notify_*`) just creates a row with the right `verb`, so adding a
  new notification type later doesn't need a migration.

## Verified

Ran `makemigrations` + `migrate` against a real SQLite db and a full
create-one-of-everything smoke test exercising every FK, M2M (through table),
and reverse relation (`job.job_skills`, `candidate.applications`,
`application.interviews`, `resume.analyses.skill_matches`, etc.) — all pass.
`python manage.py check` reports zero issues, and the request flow for apply →
recruiter-notified, schedule-interview → candidate-notified, message → candidate-
notified, and stage-change → candidate-notified has been exercised end-to-end through
Django's test client, not just checked for template errors.
