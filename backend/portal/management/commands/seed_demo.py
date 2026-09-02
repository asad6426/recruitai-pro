import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ApplicantProfile, RecruiterGoal, RecruiterProfile
from applications.models import Application, Interview, Note
from candidates.models import CandidateSkill, Certification, Education, WorkExperience
from jobs.models import Job, JobBenefit, JobRequirement, JobResponsibility, JobSkill
from organizations.models import Organization
from portal.services import run_resume_analysis
from resumes.models import Resume
from taxonomy.models import Skill

User = get_user_model()


def skill(name):
    obj, _ = Skill.objects.get_or_create(name=name)
    return obj


class Command(BaseCommand):
    help = "Seed demo data mirroring the original RecruitAI Pro mockups — safe to run once on a fresh DB."

    def handle(self, *args, **options):
        if Organization.objects.filter(name="InnovateTech").exists():
            self.stdout.write(self.style.WARNING("Demo data already present — skipping."))
            return

        today = timezone.localdate()

        # --- organizations -------------------------------------------------
        innovatetech = Organization.objects.create(
            name="InnovateTech", employee_count=180, funding_stage="Series B", industry="SaaS", is_verified=True
        )
        aether = Organization.objects.create(
            name="Aether Systems",
            description="Aether Systems builds observability tooling for engineering teams. 240 people across 14 countries, Series C, profitable since 2023.",
            employee_count=240,
            funding_stage="Series C",
            industry="SaaS",
            is_verified=True,
        )
        horizon = Organization.objects.create(
            name="Horizon Data", employee_count=90, funding_stage="Series A", industry="Data Infrastructure", is_verified=True
        )
        cloudsphere = Organization.objects.create(
            name="CloudSphere", employee_count=310, funding_stage="Series D", industry="Cloud Infrastructure", is_verified=False
        )

        # --- recruiters ------------------------------------------------------
        sarah_user = User.objects.create_user(
            username="sarah.jenkins", email="sarah@innovatetech.com", password="RecruitAI123!",
            first_name="Sarah", last_name="Jenkins", role=User.Role.RECRUITER,
        )
        sarah = RecruiterProfile.objects.create(user=sarah_user, organization=innovatetech, title="Head of Talent")

        david_user = User.objects.create_user(
            username="david.miller", email="david@innovatetech.com", password="RecruitAI123!",
            first_name="David", last_name="Miller", role=User.Role.RECRUITER,
        )
        RecruiterProfile.objects.create(user=david_user, organization=innovatetech, title="Engineering Manager")

        # --- jobs at InnovateTech (the recruiter's own org) -------------------
        def make_job(org, title, dept, emp_type, workplace, salary_min, salary_max, summary, status,
                     min_exp, skills, requirements, responsibilities, benefits, hiring_manager=None,
                     team_name="", team_size=None, published_days_ago=None, auto_shortlist=80):
            job = Job.objects.create(
                organization=org, hiring_manager=hiring_manager, title=title, department=dept,
                employment_type=emp_type, workplace=workplace, location="San Francisco, CA" if workplace != Job.Workplace.REMOTE else "Remote",
                salary_min=salary_min, salary_max=salary_max, summary=summary, min_experience_years=min_exp,
                status=status, team_name=team_name, team_size=team_size,
                auto_shortlist_threshold_pct=auto_shortlist, anonymize_screening=True,
                publish_to_careers_page=True, publish_to_linkedin=True,
                applications_close_at=today + datetime.timedelta(days=45),
            )
            if published_days_ago is not None:
                job.published_at = timezone.now() - datetime.timedelta(days=published_days_ago)
                job.save(update_fields=["published_at"])
            for i, name in enumerate(skills):
                JobSkill.objects.create(job=job, skill=skill(name), is_required=True, weight=len(skills) - i)
            for i, text in enumerate(requirements):
                JobRequirement.objects.create(job=job, text=text, order=i)
            for i, text in enumerate(responsibilities):
                JobResponsibility.objects.create(job=job, text=text, order=i)
            for i, text in enumerate(benefits):
                JobBenefit.objects.create(job=job, text=text, order=i)
            return job

        job_frontend = make_job(
            innovatetech, "Senior Frontend Developer", Job.Department.ENGINEERING, Job.EmploymentType.FULL_TIME,
            Job.Workplace.REMOTE, 150000, 190000,
            "Own the customer-facing web app end to end, from architecture to pixel-level polish.",
            Job.Status.OPEN, 5, ["React.js", "TypeScript", "Redux", "Tailwind CSS", "Next.js"],
            ["5+ years building production React applications.", "Comfortable owning architecture decisions.",
             "Strong CSS fundamentals."],
            ["Own the design and implementation of new customer-facing features.",
             "Partner with design on component architecture.", "Mentor two mid-level engineers."],
            ["Fully remote, async-first", "Equity from day one", "$3,000 annual learning budget", "30 days paid leave"],
            hiring_manager=david_user, team_name="Web Platform", team_size=8, published_days_ago=6,
        )
        job_designer = make_job(
            innovatetech, "Lead UI/UX Designer", Job.Department.DESIGN, Job.EmploymentType.FULL_TIME,
            Job.Workplace.REMOTE, 140000, 185000,
            "Own the end-to-end experience of our analytics workspace — the surface every customer starts their day on.",
            Job.Status.OPEN, 5, ["Figma", "Design Systems", "Prototyping", "User Research"],
            ["5+ years designing complex B2B or data-heavy products.",
             "Expert with Figma; comfortable building and governing design systems.",
             "Portfolio showing measurable outcomes, not just final screens."],
            ["Own the design of the analytics workspace from discovery through delivery.",
             "Extend and maintain our design system alongside the front-end guild.",
             "Run monthly research sessions and turn findings into product decisions."],
            ["Fully remote, async-first", "Equity from day one", "$3,000 annual learning budget", "30 days paid leave"],
            hiring_manager=sarah_user, team_name="Product Design", team_size=6, published_days_ago=2,
        )
        job_data = make_job(
            innovatetech, "Data Science Manager", Job.Department.DATA, Job.EmploymentType.FULL_TIME,
            Job.Workplace.ON_SITE, 180000, 240000,
            "Lead a team of data scientists building the models behind our matching engine.",
            Job.Status.OPEN, 6, ["Python", "SQL", "PyTorch"],
            ["6+ years in applied ML.", "People-management experience."],
            ["Lead a team of 4 data scientists.", "Own the roadmap for the matching model."],
            ["Equity from day one", "$3,000 annual learning budget"],
            hiring_manager=sarah_user, team_name="Data Science", team_size=5, published_days_ago=9,
        )
        make_job(
            innovatetech, "Marketing Lead", Job.Department.MARKETING, Job.EmploymentType.FULL_TIME,
            Job.Workplace.ON_SITE, 120000, 150000, "Own brand and lifecycle marketing.",
            Job.Status.DRAFT, 3, ["Content Strategy", "SEO"], [], [], [], hiring_manager=sarah_user,
        )
        make_job(
            innovatetech, "Product Manager, Platform", Job.Department.PRODUCT, Job.EmploymentType.FULL_TIME,
            Job.Workplace.HYBRID, 155000, 195000, "Own the platform team's roadmap.", Job.Status.CLOSED, 5,
            ["Roadmapping", "SQL"], [], [], [], hiring_manager=sarah_user, published_days_ago=60,
        )

        job_aether = make_job(
            aether, "Senior Product Designer", Job.Department.DESIGN, Job.EmploymentType.FULL_TIME,
            Job.Workplace.REMOTE, 140000, 185000,
            "Aether Systems is looking for a Senior Product Designer to own the end-to-end experience of our analytics workspace — the surface where every customer starts their day. You will partner with a product manager and four engineers, run your own discovery, and ship in two-week cycles.",
            Job.Status.OPEN, 5, ["Figma", "Design Systems", "Prototyping", "User Research", "Design Tokens", "Data Visualization"],
            ["5+ years designing complex B2B or data-heavy products.",
             "Expert with Figma; comfortable building and governing design systems.",
             "Portfolio showing measurable outcomes, not just final screens.",
             "Working knowledge of HTML/CSS so handoff conversations stay concrete."],
            ["Own the design of the analytics workspace from discovery through delivery.",
             "Extend and maintain our design system alongside the front-end guild.",
             "Run monthly research sessions and turn findings into product decisions.",
             "Mentor two mid-level designers and raise the bar on craft across the team."],
            ["Fully remote, async-first", "Equity from day one", "$3,000 annual learning budget", "30 days paid leave"],
            team_name="Product Design", team_size=6, published_days_ago=2,
        )
        job_horizon = make_job(
            horizon, "Data Science Manager", Job.Department.DATA, Job.EmploymentType.FULL_TIME,
            Job.Workplace.ON_SITE, 180000, 240000, "Lead our applied ML team.", Job.Status.OPEN, 6,
            ["Python", "SQL", "PyTorch"], [], [], [], team_name="Data Science", team_size=5, published_days_ago=5,
        )
        job_cloudsphere = make_job(
            cloudsphere, "Lead UX Architect", Job.Department.DESIGN, Job.EmploymentType.FULL_TIME,
            Job.Workplace.REMOTE, 165000, 210000, "Own UX architecture across our product suite.",
            Job.Status.OPEN, 7, ["Figma", "Design Systems", "React"], [], [], [], published_days_ago=1,
        )

        # --- applicants --------------------------------------------------------
        def make_applicant(email, first, last, headline, employer, location, source,
                            work_experiences, education, technical_skills, soft_skills, certifications):
            user = User.objects.create_user(
                username=email.split("@")[0], email=email, password="RecruitAI123!",
                first_name=first, last_name=last, role=User.Role.APPLICANT,
            )
            candidate = ApplicantProfile.objects.create(
                user=user, headline=headline, current_employer=employer, location=location, source=source,
                ats_score=0, profile_completion_pct=0,
            )
            for exp in work_experiences:
                WorkExperience.objects.create(candidate=candidate, **exp)
            for edu in education:
                Education.objects.create(candidate=candidate, **edu)
            for name, pct in technical_skills:
                CandidateSkill.objects.create(
                    candidate=candidate, skill=skill(name), category=CandidateSkill.Category.TECHNICAL, proficiency_pct=pct
                )
            for name in soft_skills:
                CandidateSkill.objects.create(candidate=candidate, skill=skill(name), category=CandidateSkill.Category.SOFT)
            for name in certifications:
                Certification.objects.create(candidate=candidate, name=name)
            return candidate

        alex = make_applicant(
            "alex@example.com", "Alex", "Rivera", "Senior Frontend Engineer", "TechFlow", "San Francisco, CA",
            ApplicantProfile.Source.CAREERS_PAGE,
            [
                {"title": "Senior Frontend Engineer", "company": "TechFlow", "location": "San Francisco, CA",
                 "start_date": datetime.date(2021, 3, 1), "end_date": None,
                 "description": "Led the rebuild of the customer dashboard in React, cutting load time by 40%.", "order": 0},
                {"title": "Frontend Engineer", "company": "Lumina Labs", "location": "Remote",
                 "start_date": datetime.date(2018, 6, 1), "end_date": datetime.date(2021, 2, 1),
                 "description": "Built the design system used across four product lines.", "order": 1},
            ],
            [{"degree": "BS, Computer Science", "institution": "UC Berkeley", "start_year": 2014, "end_year": 2018}],
            [("React.js", 95), ("TypeScript", 88), ("Redux", 82), ("Tailwind CSS", 78), ("HTML/CSS/JS", 92), ("Next.js", 60)],
            ["Stakeholder Management", "Mentorship"], ["Meta Front-End Developer Certificate"],
        )
        alexandria = make_applicant(
            "alexandria@example.com", "Alexandria", "Moore", "Senior Product Designer", "FintechFlow", "New York, NY",
            ApplicantProfile.Source.LINKEDIN,
            [
                {"title": "Senior Product Designer", "company": "FintechFlow", "location": "San Francisco, CA",
                 "start_date": datetime.date(2020, 1, 1), "end_date": None,
                 "description": "Led a team of 4 designers to modernize the core banking dashboard. Increased user engagement by 32% through data-driven UX enhancements.", "order": 0},
                {"title": "UX Designer", "company": "CloudSync Solutions", "location": "Seattle, WA",
                 "start_date": datetime.date(2017, 6, 1), "end_date": datetime.date(2019, 12, 1),
                 "description": "Owned onboarding and billing flows for a B2B storage product.", "order": 1},
            ],
            [{"degree": "BFA, Interaction Design", "institution": "Rhode Island School of Design", "start_year": 2011, "end_year": 2015}],
            [("Figma", 95), ("Design Systems", 92), ("Prototyping", 80), ("User Research", 74), ("HTML/CSS/JS", 65)],
            ["Stakeholder Management", "Design Mentorship", "Strategic Planning"],
            ["NN/g UX Certification", "IAAP CPACC (Accessibility)"],
        )
        david_chen = make_applicant(
            "davidchen@example.com", "David", "Chen", "Full Stack Developer", "TechNova", "Austin, TX",
            ApplicantProfile.Source.REFERRAL,
            [{"title": "Full Stack Developer", "company": "TechNova", "location": "Austin, TX",
              "start_date": datetime.date(2019, 4, 1), "end_date": None,
              "description": "Ships production systems end to end; scaled a payments API to 40k requests per minute.", "order": 0}],
            [{"degree": "BS, Computer Science", "institution": "UT Austin", "start_year": 2011, "end_year": 2015}],
            [("Node.js", 90), ("React.js", 85), ("PostgreSQL", 80), ("AWS", 75), ("GraphQL", 70)],
            ["Ownership"], [],
        )
        elena = make_applicant(
            "elena@example.com", "Elena", "Rodriguez", "Product Manager", "Horizon Data", "Boston, MA",
            ApplicantProfile.Source.CAREERS_PAGE,
            [{"title": "Product Manager", "company": "Horizon Data", "location": "Boston, MA",
              "start_date": datetime.date(2020, 8, 1), "end_date": None,
              "description": "Took two B2B products from zero to first revenue.", "order": 0}],
            [{"degree": "MBA", "institution": "Boston University", "start_year": 2016, "end_year": 2018}],
            [("SQL", 78), ("Roadmapping", 88)], ["Stakeholder Management", "Experimentation"], [],
        )
        li_wei = make_applicant(
            "liwei@example.com", "Li", "Wei", "Data Analyst", "DataPeak", "Seattle, WA",
            ApplicantProfile.Source.LINKEDIN,
            [{"title": "Data Analyst", "company": "DataPeak", "location": "Seattle, WA",
              "start_date": datetime.date(2021, 1, 1), "end_date": None,
              "description": "Built the reporting pipeline used by the exec team.", "order": 0}],
            [{"degree": "BS, Statistics", "institution": "University of Washington", "start_year": 2016, "end_year": 2020}],
            [("SQL", 85), ("Python", 80)], ["Analytics"], [],
        )

        # --- resumes -------------------------------------------------------
        resume_alex = Resume.objects.create(candidate=alex, filename="Resume_Frontend_2024.pdf", is_primary=True)
        resume_alexandria = Resume.objects.create(candidate=alexandria, filename="Resume_Design_2024.pdf", is_primary=True)
        resume_david = Resume.objects.create(candidate=david_chen, filename="Resume_DavidChen.pdf", is_primary=True)
        resume_elena = Resume.objects.create(candidate=elena, filename="Resume_ElenaRodriguez.pdf", is_primary=True)
        resume_li = Resume.objects.create(candidate=li_wei, filename="Resume_LiWei.pdf", is_primary=True)

        # --- applications + real (rule-based) resume analyses -----------------
        def apply(candidate, resume, job, stage, source, days_ago):
            application = Application.objects.create(
                candidate=candidate, job=job, resume=resume, stage=stage, source=source,
                consent_given=True, note_to_hiring_team="",
            )
            application.applied_at = timezone.now() - datetime.timedelta(days=days_ago)
            application.save(update_fields=["applied_at"])
            analysis = run_resume_analysis(resume, job)
            application.ats_score = analysis.overall_match_pct
            application.match_pct = analysis.overall_match_pct
            application.save(update_fields=["ats_score", "match_pct"])
            candidate.ats_score = analysis.overall_match_pct
            candidate.save(update_fields=["ats_score"])
            return application

        app1 = apply(alexandria, resume_alexandria, job_designer, Application.Stage.SHORTLISTED, Application.Source.CAREERS_PAGE, 2)
        app2 = apply(david_chen, resume_david, job_frontend, Application.Stage.INTERVIEW, Application.Source.REFERRAL, 5)
        app3 = apply(li_wei, resume_li, job_data, Application.Stage.TECHNICAL_TEST, Application.Source.LINKEDIN, 1)
        app4 = apply(elena, resume_elena, job_frontend, Application.Stage.REVIEW, Application.Source.CAREERS_PAGE, 3)
        app5 = apply(alex, resume_alex, job_frontend, Application.Stage.NEW_APPLIED, Application.Source.CAREERS_PAGE, 0)
        apply(alexandria, resume_alexandria, job_data, Application.Stage.OFFER, Application.Source.CAREERS_PAGE, 10)
        apply(alex, resume_alex, job_designer, Application.Stage.HIRED, Application.Source.REFERRAL, 20)
        apply(li_wei, resume_li, job_frontend, Application.Stage.REJECTED, Application.Source.LINKEDIN, 15)

        # Alex also applies to an external job so his applicant dashboard shows real data.
        apply(alex, resume_alex, job_aether, Application.Stage.REVIEW, Application.Source.CAREERS_PAGE, 4)

        # --- interviews ---------------------------------------------------
        Interview.objects.create(
            application=app2, interviewer=david_user,
            scheduled_at=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0),
            mode=Interview.Mode.VIDEO, status=Interview.Status.SCHEDULED,
        )
        Interview.objects.create(
            application=app1, interviewer=sarah_user,
            scheduled_at=timezone.now().replace(hour=11, minute=30, second=0, microsecond=0),
            mode=Interview.Mode.PANEL, status=Interview.Status.SCHEDULED,
        )
        Interview.objects.create(
            application=app5, interviewer=david_user,
            scheduled_at=timezone.now() + datetime.timedelta(days=3, hours=2),
            mode=Interview.Mode.VIDEO, status=Interview.Status.SCHEDULED,
        )

        # --- notes ----------------------------------------------------------
        Note.objects.create(candidate=alexandria, author=sarah_user,
                             body="Impressive portfolio. Her work at FintechFlow shows a high level of systematic thinking. Definitely worth moving to the final stage.")
        Note.objects.create(candidate=alexandria, author=david_user,
                             body="Paired with her on the design-system walkthrough. She reasons about component APIs the way an engineer would — handoff would be painless.")
        Note.objects.create(candidate=david_chen, author=sarah_user,
                             body="Strong technical interview. Notice period is 4 weeks.")

        # --- recruiter goal ---------------------------------------------------
        RecruiterGoal.objects.create(
            recruiter=sarah, period_start=today.replace(day=1),
            period_end=(today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1),
            target_hires=20, current_hires=1,
        )

        # --- saved jobs -------------------------------------------------------
        from jobs.models import SavedJob
        SavedJob.objects.create(applicant=alex, job=job_cloudsphere)
        SavedJob.objects.create(applicant=alex, job=job_horizon)

        self.stdout.write(self.style.SUCCESS(
            "Seeded 4 organizations, 2 recruiters, 5 applicants, 8 jobs, 9 applications, real resume analyses, "
            "3 interviews, 3 notes, 1 recruiter goal.\n"
            "Login as recruiter: sarah@innovatetech.com / RecruitAI123!\n"
            "Login as applicant: alex@example.com / RecruitAI123!"
        ))
