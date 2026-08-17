# RecruitAI Pro — Backend Schema

Django project modeling the data behind the `recruitai-pro/` frontend prototype.
Schema only — no views/APIs wired up yet.

## Run it

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then open `/admin/` to browse and create data through Django admin (every model
is registered).

## App layout

| App | Models | Backs |
|---|---|---|
| `accounts` | `User`, `RecruiterProfile`, `ApplicantProfile`, `RecruiterGoal` | login/signup/role-select, the logged-in identity in every page's topbar, the dashboard "Recruiter Goal" card |
| `organizations` | `Organization` | the company on a job posting / "About [Company]" card on job-details.html |
| `taxonomy` | `Skill` | shared skill vocabulary reused by jobs, candidates, and resume analysis |
| `jobs` | `Job`, `JobSkill`, `JobRequirement`, `JobResponsibility`, `JobBenefit`, `SavedJob` | post-job.html, jobs.html, browse-jobs.html, job-details.html |
| `candidates` | `WorkExperience`, `Education`, `CandidateSkill`, `Certification` | candidate-profile.html Overview/Experience/Skills tabs |
| `resumes` | `Resume`, `ResumeAnalysis`, `ResumeSkillMatch`, `OptimizationSuggestion` | resume-analysis.html |
| `applications` | `Application`, `Note`, `Interview` | candidates.html table + drawer, candidate-profile.html Notes tab, dashboard "Interviews Today" |

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
- Sidebar items marked "Soon" in the frontend (Interviews list beyond
  today, Analytics, Notifications, Settings, Skill Insights) have no models
  yet — `Interview` exists because it's already used by the dashboard's
  "Interviews Today" card, but there's no notification/analytics schema.

## Verified

Ran `makemigrations` + `migrate` against a real SQLite db and a full
create-one-of-everything smoke test exercising every FK, M2M (through table),
and reverse relation (`job.job_skills`, `candidate.applications`,
`application.interviews`, `resume.analyses.skill_matches`, etc.) — all pass.
`python manage.py check` reports zero issues.
