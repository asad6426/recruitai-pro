from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import ApplicantProfile, RecruiterGoal, User
from applications.models import Application, Interview, Note
from candidates.models import CandidateSkill
from jobs.models import Job, JobBenefit, JobRequirement, JobResponsibility, JobSkill
from notifications.models import Notification
from resumes.models import OptimizationSuggestion, ResumeAnalysis, ResumeSkillMatch
from taxonomy.models import Skill

from . import services
from .decorators import role_required
from .forms import (
    InterviewForm,
    JobForm,
    MessageCandidateForm,
    NoteForm,
    PasswordChangeForm,
    RecruiterProfileForm,
)


def _org(request):
    return request.user.recruiter_profile.organization


def _skills_ordered_for(application):
    """Candidate's skill names, with skills that matched THIS job listed
    first — keeps candidates.js's 'first three chips are matches' convention
    correct without touching the JS."""
    candidate = application.candidate
    all_skills = list(candidate.skills.select_related("skill").values_list("skill__name", flat=True))
    if not application.resume:
        return all_skills
    matched_names = set(
        ResumeSkillMatch.objects.filter(
            analysis__resume=application.resume,
            analysis__job=application.job,
            status=ResumeSkillMatch.MatchStatus.MATCHED,
        ).values_list("skill__name", flat=True)
    )
    return [s for s in all_skills if s in matched_names] + [s for s in all_skills if s not in matched_names]


def _candidate_row(application):
    candidate = application.candidate
    latest_analysis = None
    if application.resume:
        latest_analysis = (
            ResumeAnalysis.objects.filter(resume=application.resume, job=application.job)
            .order_by("-analyzed_at")
            .first()
        )
    return {
        "application": application,
        "name": candidate.user.get_full_name() or candidate.user.email,
        "email": candidate.user.email,
        "skills": _skills_ordered_for(application),
        "insight": latest_analysis.ai_insight if latest_analysis else "",
    }


@role_required("recruiter")
def dashboard(request):
    org = _org(request)
    applications = Application.objects.filter(job__organization=org)
    jobs = Job.objects.filter(organization=org)

    total_applied = applications.count()
    reached_screening = applications.exclude(
        stage__in=[Application.Stage.NEW_APPLIED, Application.Stage.REJECTED]
    ).count()
    reached_interview = applications.filter(
        stage__in=[
            Application.Stage.TECHNICAL_TEST,
            Application.Stage.INTERVIEW,
            Application.Stage.SHORTLISTED,
            Application.Stage.OFFER,
            Application.Stage.HIRED,
        ]
    ).count()
    reached_offer = applications.filter(
        stage__in=[Application.Stage.SHORTLISTED, Application.Stage.OFFER, Application.Stage.HIRED]
    ).count()
    reached_hired = applications.filter(stage=Application.Stage.HIRED).count()
    funnel_base = total_applied or 1
    funnel = [
        {"label": "Applied", "count": total_applied, "height": round(total_applied / funnel_base * 100)},
        {"label": "Screening", "count": reached_screening, "height": round(reached_screening / funnel_base * 100)},
        {"label": "Interviews", "count": reached_interview, "height": round(reached_interview / funnel_base * 100)},
        {"label": "Offer", "count": reached_offer, "height": round(reached_offer / funnel_base * 100)},
        {"label": "Hired", "count": reached_hired, "height": round(reached_hired / funnel_base * 100)},
    ]

    today = timezone.localdate()
    interviews_today = (
        Interview.objects.filter(application__job__organization=org, scheduled_at__date=today)
        .select_related("application__candidate__user", "application__job")
        .order_by("scheduled_at")
    )

    goal = (
        RecruiterGoal.objects.filter(recruiter=request.user.recruiter_profile).order_by("-period_end").first()
    )
    goal_current_hires = reached_hired
    goal_pct = round(goal_current_hires / goal.target_hires * 100) if goal and goal.target_hires else 0

    context = {
        "active_nav": "dashboard",
        "page_title": "Recruiter Dashboard",
        "total_candidates": applications.values("candidate").distinct().count(),
        "total_candidates_trend": services.period_trend_pct(applications, "applied_at"),
        "active_jobs": jobs.filter(status=Job.Status.OPEN).count(),
        "shortlisted": applications.filter(stage=Application.Stage.SHORTLISTED).count(),
        "interviews_today": interviews_today,
        "avg_time_to_hire": services.avg_time_to_hire(applications),
        "recent_applications": applications.select_related("candidate__user", "job").order_by("-applied_at")[:3],
        "funnel": funnel,
        "goal": goal,
        "goal_pct": goal_pct,
        "goal_current_hires": goal_current_hires,
        "pending_offers": reached_offer - reached_hired,
    }
    return render(request, "recruiter/dashboard.html", context)


@role_required("recruiter")
def candidate_list(request):
    org = _org(request)
    applications = (
        Application.objects.filter(job__organization=org)
        .select_related("candidate__user", "job")
        .order_by("-applied_at")
    )

    job_id = request.GET.get("job")
    if job_id:
        applications = applications.filter(job_id=job_id)
    min_score = request.GET.get("min_score")
    if min_score:
        applications = applications.filter(ats_score__gte=min_score)
    stage = request.GET.get("stage")
    if stage:
        applications = applications.filter(stage=stage)

    rows = [_candidate_row(a) for a in applications]
    jobs_with_applications = Job.objects.filter(organization=org, applications__isnull=False).distinct()

    context = {
        "active_nav": "candidates",
        "page_title": "Candidates",
        "rows": rows,
        "total_count": Application.objects.filter(job__organization=org).count(),
        "jobs_with_applications": jobs_with_applications,
    }
    return render(request, "recruiter/candidates.html", context)


@role_required("recruiter")
def candidate_profile(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("candidate__user", "job__organization"),
        pk=application_id,
        job__organization=_org(request),
    )
    candidate = application.candidate

    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            Note.objects.create(candidate=candidate, author=request.user, body=form.cleaned_data["body"])
            messages.success(request, "Note saved.")
            return redirect("recruiter_candidate_profile", application_id=application.pk)
    else:
        form = NoteForm()

    latest_analysis = None
    if application.resume:
        latest_analysis = (
            ResumeAnalysis.objects.filter(resume=application.resume, job=application.job)
            .order_by("-analyzed_at")
            .first()
        )

    notes = (
        Note.objects.filter(candidate=candidate)
        .select_related("author__recruiter_profile")
        .order_by("-created_at")
    )

    context = {
        "active_nav": "candidates",
        "page_title": "Candidate Profile",
        "application": application,
        "candidate": candidate,
        "work_experiences": candidate.work_experiences.all(),
        "education": candidate.education.all(),
        "technical_skills": candidate.skills.filter(category=CandidateSkill.Category.TECHNICAL).select_related(
            "skill"
        ),
        "soft_skills": candidate.skills.filter(category=CandidateSkill.Category.SOFT).select_related("skill"),
        "certifications": candidate.certifications.all(),
        "notes": notes,
        "notes_count": notes.count(),
        "latest_analysis": latest_analysis,
        "summary_text": services.candidate_summary(candidate, latest_analysis),
        "note_form": form,
    }
    return render(request, "recruiter/candidate_profile.html", context)


@role_required("recruiter")
def resume_analysis(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("candidate__user", "job__organization"),
        pk=application_id,
        job__organization=_org(request),
    )
    analysis = None
    if application.resume:
        analysis = (
            ResumeAnalysis.objects.filter(resume=application.resume, job=application.job)
            .order_by("-analyzed_at")
            .first()
        )

    if request.method == "POST":
        if application.resume:
            analysis = services.run_resume_analysis(application.resume, application.job)
            application.ats_score = analysis.overall_match_pct
            application.match_pct = analysis.overall_match_pct
            application.save(update_fields=["ats_score", "match_pct"])
            messages.success(request, "Score recalculated.")
        else:
            messages.error(request, "This candidate has no resume on file yet.")
        return redirect("recruiter_resume_analysis", application_id=application.pk)

    skill_matches = (
        ResumeSkillMatch.objects.filter(analysis=analysis).select_related("skill") if analysis else []
    )
    matched = [m.skill.name for m in skill_matches if m.status == ResumeSkillMatch.MatchStatus.MATCHED]
    partial = [m.skill.name for m in skill_matches if m.status == ResumeSkillMatch.MatchStatus.PARTIAL]
    missing = [m.skill.name for m in skill_matches if m.status == ResumeSkillMatch.MatchStatus.MISSING]
    suggestions = OptimizationSuggestion.objects.filter(analysis=analysis) if analysis else []

    context = {
        "active_nav": "candidates",
        "page_title": "Resume Analysis",
        "application": application,
        "analysis": analysis,
        "matched_skills": matched,
        "partial_skills": partial,
        "missing_skills": missing,
        "suggestions": suggestions,
        "top_percentile_label": services.top_percentile_label(analysis) if analysis else None,
        "onboarding_label": services.onboarding_estimate_label(analysis.experience_relevancy_pct)
        if analysis
        else None,
    }
    return render(request, "recruiter/resume_analysis.html", context)


@role_required("recruiter")
def jobs_list(request):
    org = _org(request)
    jobs = Job.objects.filter(organization=org).order_by("-created_at")

    status = request.GET.get("status")
    if status:
        jobs = jobs.filter(status=status)
    dept = request.GET.get("dept")
    if dept:
        jobs = jobs.filter(department=dept)

    job_rows = [
        {"job": job, "applicant_count": job.applications.count(), "fill_pct": services.pipeline_fill_pct(job)}
        for job in jobs
    ]

    all_org_applications = Application.objects.filter(job__organization=org)
    context = {
        "active_nav": "jobs",
        "page_title": "Job Postings",
        "job_rows": job_rows,
        "active_jobs_count": Job.objects.filter(organization=org, status=Job.Status.OPEN).count(),
        "drafts_count": Job.objects.filter(organization=org, status=Job.Status.DRAFT).count(),
        "total_applicants": all_org_applications.count(),
        "avg_time_to_fill": services.avg_time_to_hire(all_org_applications),
        "department_choices": Job.Department.choices,
        "status_choices": Job.Status.choices,
    }
    return render(request, "recruiter/jobs.html", context)


@role_required("recruiter")
def post_job(request, job_id=None):
    org = _org(request)
    job = get_object_or_404(Job, pk=job_id, organization=org) if job_id else None

    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            if job is None:
                job = Job(organization=org)
            job.title = cd["jobTitle"]
            job.department = cd["jobDept"]
            job.employment_type = cd["jobType"]
            job.location = cd["jobLocation"]
            job.workplace = cd["jobWorkplace"]
            job.salary_min = cd["salaryMin"]
            job.salary_max = cd["salaryMax"]
            job.summary = cd["jobSummary"]
            job.team_name = cd["teamName"]
            job.team_size = cd["teamSize"]
            job.min_experience_years = int(cd["minExperience"] or 0)
            job.auto_shortlist_threshold_pct = (
                None if not cd["atsThreshold"] or cd["atsThreshold"] == "off" else int(cd["atsThreshold"])
            )
            job.auto_reject_threshold_pct = 40 if cd["autoReject"] else None
            job.anonymize_screening = cd["anonScreen"]
            job.hiring_manager_id = cd["hiringManager"] or None
            job.applications_close_at = cd["closeDate"]
            job.publish_to_careers_page = cd["chCareers"]
            job.publish_to_linkedin = cd["chLinkedin"]
            job.publish_to_partner_boards = cd["chBoard"]

            action = request.POST.get("action", "publish")
            if action == "draft":
                job.status = Job.Status.DRAFT
            else:
                job.status = Job.Status.OPEN
                if not job.published_at:
                    job.published_at = timezone.now()
            job.save()

            job.requirements.all().delete()
            for i, line in enumerate(l.strip() for l in cd["jobRequirements"].splitlines() if l.strip()):
                JobRequirement.objects.create(job=job, text=line, order=i)
            job.responsibilities.all().delete()
            for i, line in enumerate(l.strip() for l in cd["jobResponsibilities"].splitlines() if l.strip()):
                JobResponsibility.objects.create(job=job, text=line, order=i)
            job.benefits.all().delete()
            for i, line in enumerate(l.strip() for l in cd["jobBenefits"].splitlines() if l.strip()):
                JobBenefit.objects.create(job=job, text=line, order=i)

            job.job_skills.all().delete()
            for name in (s.strip() for s in cd["jobSkills"].split(",") if s.strip()):
                skill, _ = Skill.objects.get_or_create(name=name)
                JobSkill.objects.create(job=job, skill=skill, is_required=True, weight=1)

            messages.success(
                request, "Draft saved." if action == "draft" else "Job posted — screening starts now."
            )
            return redirect("recruiter_jobs")
    else:
        if job:
            join_lines = lambda qs: "\n".join(qs.values_list("text", flat=True))
            form = JobForm(
                initial={
                    "jobTitle": job.title,
                    "jobDept": job.department,
                    "jobType": job.employment_type,
                    "jobLocation": job.location,
                    "jobWorkplace": job.workplace,
                    "salaryMin": job.salary_min,
                    "salaryMax": job.salary_max,
                    "jobSummary": job.summary,
                    "jobRequirements": join_lines(job.requirements.all()),
                    "jobResponsibilities": join_lines(job.responsibilities.all()),
                    "jobBenefits": join_lines(job.benefits.all()),
                    "jobSkills": ", ".join(job.skills.values_list("name", flat=True)),
                    "teamName": job.team_name,
                    "teamSize": job.team_size,
                    "minExperience": str(job.min_experience_years)
                    if job.min_experience_years in (0, 2, 5, 8)
                    else "",
                    "atsThreshold": str(job.auto_shortlist_threshold_pct)
                    if job.auto_shortlist_threshold_pct
                    else "off",
                    "anonScreen": job.anonymize_screening,
                    "autoReject": bool(job.auto_reject_threshold_pct),
                    "hiringManager": job.hiring_manager_id,
                    "closeDate": job.applications_close_at,
                    "chCareers": job.publish_to_careers_page,
                    "chLinkedin": job.publish_to_linkedin,
                    "chBoard": job.publish_to_partner_boards,
                }
            )
        else:
            form = JobForm(
                initial={"anonScreen": True, "chCareers": True, "chLinkedin": True, "minExperience": "5", "atsThreshold": "80"}
            )

    hiring_managers = User.objects.filter(role="recruiter", recruiter_profile__organization=org)
    context = {
        "active_nav": "jobs",
        "page_title": "Edit Job Posting" if job else "Post a New Job",
        "form": form,
        "job": job,
        "hiring_managers": hiring_managers,
        "expected_reach": ApplicantProfile.objects.count(),
    }
    return render(request, "recruiter/post_job.html", context)


@role_required("recruiter")
@require_POST
def application_stage_update(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__organization=_org(request))
    stage = request.POST.get("stage")
    if stage in Application.Stage.values:
        application.stage = stage
        application.save(update_fields=["stage"])
        services.notify_stage_changed(application, request.user)
        messages.success(request, f"Candidate marked as {application.get_stage_display()}.")
    return redirect(request.POST.get("next") or "recruiter_candidates")


@role_required("recruiter")
@require_POST
def interview_schedule(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__organization=_org(request))
    form = InterviewForm(request.POST)
    if form.is_valid():
        interview = Interview.objects.create(
            application=application,
            interviewer=request.user,
            scheduled_at=form.cleaned_data["scheduled_at"],
            mode=form.cleaned_data["mode"],
        )
        services.notify_interview_scheduled(interview)
        messages.success(request, "Interview scheduled.")
    else:
        messages.error(request, "Could not schedule interview — check the date/time.")
    return redirect("recruiter_candidate_profile", application_id=application.pk)


@role_required("recruiter")
@require_POST
def message_candidate(request, application_id):
    application = get_object_or_404(Application, pk=application_id, job__organization=_org(request))
    form = MessageCandidateForm(request.POST)
    if form.is_valid():
        Notification.objects.create(
            recipient=application.candidate.user,
            sender=request.user,
            application=application,
            verb=Notification.Verb.MESSAGE,
            message=form.cleaned_data["body"],
        )
        messages.success(request, f"Message sent to {application.candidate.user.get_full_name()}.")
    else:
        messages.error(request, "Write a message before sending.")

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("recruiter_candidate_profile", application_id=application.pk)


@role_required("recruiter")
def interviews_list(request):
    org = _org(request)
    interviews = (
        Interview.objects.filter(application__job__organization=org)
        .select_related("application__candidate__user", "application__job")
        .order_by("scheduled_at")
    )
    now = timezone.now()
    context = {
        "active_nav": "interviews",
        "page_title": "Interviews",
        "upcoming": interviews.filter(scheduled_at__gte=now),
        "past": interviews.filter(scheduled_at__lt=now).order_by("-scheduled_at"),
    }
    return render(request, "recruiter/interviews.html", context)


@role_required("recruiter")
def analytics(request):
    org = _org(request)
    applications = Application.objects.filter(job__organization=org)
    jobs = Job.objects.filter(organization=org)

    stage_breakdown = [
        {"label": label, "count": applications.filter(stage=value).count()}
        for value, label in Application.Stage.choices
    ]
    source_breakdown = [
        {"label": label, "count": applications.filter(source=value).count()}
        for value, label in Application.Source.choices
        if applications.filter(source=value).exists()
    ]
    top_jobs = jobs.annotate(applicant_count=Count("applications")).order_by("-applicant_count")[:5]

    context = {
        "active_nav": "analytics",
        "page_title": "Analytics",
        "total_applications": applications.count(),
        "applications_trend": services.period_trend_pct(applications, "applied_at"),
        "avg_time_to_hire": services.avg_time_to_hire(applications),
        "active_jobs": jobs.filter(status=Job.Status.OPEN).count(),
        "hired_count": applications.filter(stage=Application.Stage.HIRED).count(),
        "stage_breakdown": stage_breakdown,
        "stage_max": max((s["count"] for s in stage_breakdown), default=0) or 1,
        "source_breakdown": source_breakdown,
        "top_jobs": top_jobs,
        "top_jobs_max": max((j.applicant_count for j in top_jobs), default=0) or 1,
    }
    return render(request, "recruiter/analytics.html", context)


@role_required("recruiter")
def notifications_list(request):
    notifications = list(
        Notification.objects.filter(recipient=request.user).select_related("sender", "application__job")
    )
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    context = {"active_nav": "notifications", "page_title": "Notifications", "notifications": notifications}
    return render(request, "recruiter/notifications.html", context)


@role_required("recruiter")
def settings_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated.")
            return redirect("recruiter_settings")
    else:
        form = PasswordChangeForm(request.user)

    context = {"active_nav": "settings", "page_title": "Settings", "form": form}
    return render(request, "recruiter/settings.html", context)


@role_required("recruiter")
@require_POST
def job_status_update(request, job_id):
    job = get_object_or_404(Job, pk=job_id, organization=_org(request))
    status = request.POST.get("status")
    if status in (Job.Status.OPEN, Job.Status.PAUSED, Job.Status.CLOSED):
        job.status = status
        if status == Job.Status.OPEN and not job.published_at:
            job.published_at = timezone.now()
        job.save(update_fields=["status", "published_at"])
        messages.success(request, f"{job.title} marked as {job.get_status_display()}.")
    return redirect("recruiter_jobs")


@role_required("recruiter")
@require_POST
def job_delete_draft(request, job_id):
    job = get_object_or_404(Job, pk=job_id, organization=_org(request), status=Job.Status.DRAFT)
    job.delete()
    messages.success(request, "Draft deleted.")
    return redirect("recruiter_jobs")


@role_required("recruiter")
def profile_edit(request):
    profile = request.user.recruiter_profile
    user = request.user
    if request.method == "POST":
        form = RecruiterProfileForm(request.POST, request.FILES)
        if form.is_valid():
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            if form.cleaned_data["avatar"]:
                user.avatar = form.cleaned_data["avatar"]
            user.save()
            profile.title = form.cleaned_data["title"]
            profile.save()
            messages.success(request, "Profile updated.")
            return redirect("recruiter_profile_edit")
    else:
        form = RecruiterProfileForm(
            initial={"first_name": user.first_name, "last_name": user.last_name, "title": profile.title}
        )

    context = {"active_nav": "profile", "page_title": "Your Profile", "profile": profile, "form": form}
    return render(request, "recruiter/profile.html", context)


@role_required("recruiter")
@require_POST
def suggestion_toggle(request, suggestion_id):
    suggestion = get_object_or_404(
        OptimizationSuggestion, pk=suggestion_id, analysis__job__organization=_org(request)
    )
    suggestion.is_addressed = not suggestion.is_addressed
    suggestion.save(update_fields=["is_addressed"])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"is_addressed": suggestion.is_addressed})
    return redirect("recruiter_candidates")
