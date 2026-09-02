from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from applications.models import Application, Interview
from candidates.models import CandidateSkill
from jobs.models import Job, SavedJob
from notifications.models import Notification
from resumes.models import OptimizationSuggestion, Resume, ResumeAnalysis, ResumeSkillMatch

from . import services
from .decorators import role_required
from .forms import ApplicantProfileForm, ApplyForm, PasswordChangeForm, ResumeUploadForm


def _candidate(request):
    return request.user.applicant_profile


@role_required("applicant")
def dashboard(request):
    candidate = _candidate(request)
    applications = (
        Application.objects.filter(candidate=candidate).select_related("job__organization").order_by("-applied_at")
    )
    resumes = candidate.resumes.all()
    primary_resume = resumes.filter(is_primary=True).first() or resumes.first()

    applied_job_ids = applications.values_list("job_id", flat=True)
    candidates_jobs = (
        Job.objects.filter(status=Job.Status.OPEN).exclude(id__in=applied_job_ids).select_related("organization")
    )
    recommended = sorted(
        ((services.match_percent_for(candidate, job) or 0, job) for job in candidates_jobs),
        key=lambda t: t[0],
        reverse=True,
    )[:4]

    resume_score = services.resume_score_for(primary_resume) if primary_resume else candidate.ats_score

    top_suggestion = None
    if primary_resume:
        latest_analysis = ResumeAnalysis.objects.filter(resume=primary_resume).order_by("-analyzed_at").first()
        if latest_analysis:
            top_suggestion = (
                OptimizationSuggestion.objects.filter(analysis=latest_analysis).order_by("-impact").first()
            )

    context = {
        "active_nav": "dashboard",
        "candidate": candidate,
        "applications": applications[:3],
        "total_applications": applications.count(),
        "upcoming_interviews": Interview.objects.filter(
            application__candidate=candidate, scheduled_at__gte=timezone.now()
        ).order_by("scheduled_at"),
        "resume_score": resume_score,
        "ats_trend": services.ats_trend_pct(candidate),
        "profile_completion": services.profile_completion_breakdown(candidate),
        "primary_resume": primary_resume,
        "top_suggestion": top_suggestion,
        "recommended": recommended,
        "activity": services.recent_activity(candidate, limit=5),
    }
    return render(request, "applicant/dashboard.html", context)


@role_required("applicant")
def browse_jobs(request):
    candidate = _candidate(request)
    jobs = Job.objects.filter(status=Job.Status.OPEN).select_related("organization").order_by("-published_at")

    q = request.GET.get("q")
    if q:
        jobs = jobs.filter(Q(title__icontains=q) | Q(organization__name__icontains=q))
    location = request.GET.get("location")
    if location:
        jobs = jobs.filter(location__icontains=location)

    saved_job_ids = set(SavedJob.objects.filter(applicant=candidate).values_list("job_id", flat=True))

    job_rows = [
        {
            "job": job,
            "match_pct": services.match_percent_for(candidate, job) or 0,
            "skills": list(job.skills.values_list("name", flat=True)),
            "is_saved": job.id in saved_job_ids,
            "posted_days_ago": (timezone.now() - job.published_at).days if job.published_at else 0,
        }
        for job in jobs
    ]

    context = {
        "active_nav": "jobs",
        "job_rows": job_rows,
        "total_jobs": jobs.count(),
        "saved_count": SavedJob.objects.filter(applicant=candidate).count(),
    }
    return render(request, "applicant/browse_jobs.html", context)


@role_required("applicant")
def job_detail(request, job_id):
    candidate = _candidate(request)
    job = get_object_or_404(Job.objects.select_related("organization"), pk=job_id)

    match_pct = services.match_percent_for(candidate, job)
    primary_resume = candidate.resumes.filter(is_primary=True).first() or candidate.resumes.first()
    analysis = None
    if primary_resume:
        analysis = (
            ResumeAnalysis.objects.filter(resume=primary_resume, job=job).order_by("-analyzed_at").first()
        )

    have_skills, worth_adding = [], []
    if analysis:
        matches = ResumeSkillMatch.objects.filter(analysis=analysis).select_related("skill")
        have_skills = [m.skill.name for m in matches if m.status == ResumeSkillMatch.MatchStatus.MATCHED]
        worth_adding = [m.skill.name for m in matches if m.status != ResumeSkillMatch.MatchStatus.MATCHED]
    else:
        candidate_skill_names = set(candidate.skills.values_list("skill__name", flat=True))
        for js in job.job_skills.select_related("skill"):
            (have_skills if js.skill.name in candidate_skill_names else worth_adding).append(js.skill.name)

    context = {
        "active_nav": "jobs",
        "job": job,
        "match_pct": match_pct,
        "analysis": analysis,
        "have_skills": have_skills,
        "worth_adding": worth_adding,
        "is_saved": SavedJob.objects.filter(applicant=candidate, job=job).exists(),
        "already_applied": Application.objects.filter(candidate=candidate, job=job).exists(),
        "resumes": [(r, services.resume_score_for(r)) for r in candidate.resumes.all()],
        "posted_days_ago": (timezone.now() - job.published_at).days if job.published_at else 0,
    }
    return render(request, "applicant/job_detail.html", context)


@role_required("applicant")
@require_POST
def apply(request, job_id):
    candidate = _candidate(request)
    job = get_object_or_404(Job, pk=job_id)
    form = ApplyForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please choose a resume and accept the consent checkbox.")
        return redirect("applicant_job_detail", job_id=job.pk)

    resume = get_object_or_404(Resume, pk=form.cleaned_data["resume_id"], candidate=candidate)
    try:
        application = Application.objects.create(
            candidate=candidate,
            job=job,
            resume=resume,
            source=Application.Source.CAREERS_PAGE,
            note_to_hiring_team=form.cleaned_data["note"],
            consent_given=form.cleaned_data["consent"],
            match_pct=services.match_percent_for(candidate, job),
            ats_score=services.resume_score_for(resume),
        )
        if not ResumeAnalysis.objects.filter(resume=resume, job=job).exists():
            services.run_resume_analysis(resume, job)
        services.notify_new_application(application)
        messages.success(request, f"Application submitted to {job.organization.name}.")
    except IntegrityError:
        messages.info(request, "You've already applied to this job.")
    return redirect("applicant_job_detail", job_id=job.pk)


@role_required("applicant")
@require_POST
def saved_job_toggle(request, job_id):
    candidate = _candidate(request)
    job = get_object_or_404(Job, pk=job_id)
    saved, created = SavedJob.objects.get_or_create(applicant=candidate, job=job)
    if not created:
        saved.delete()
        return JsonResponse({"saved": False})
    return JsonResponse({"saved": True})


@role_required("applicant")
def profile_edit(request):
    candidate = _candidate(request)
    user = request.user
    if request.method == "POST":
        form = ApplicantProfileForm(request.POST, request.FILES)
        if form.is_valid():
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            if form.cleaned_data["avatar"]:
                user.avatar = form.cleaned_data["avatar"]
            user.save()
            candidate.headline = form.cleaned_data["headline"]
            candidate.current_employer = form.cleaned_data["current_employer"]
            candidate.location = form.cleaned_data["location"]
            candidate.save()
            messages.success(request, "Profile updated.")
            return redirect("applicant_profile_edit")
    else:
        form = ApplicantProfileForm(
            initial={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "headline": candidate.headline,
                "current_employer": candidate.current_employer,
                "location": candidate.location,
            }
        )

    context = {"active_nav": "profile", "candidate": candidate, "form": form}
    return render(request, "applicant/profile.html", context)


@role_required("applicant")
@require_POST
def resume_upload(request):
    candidate = _candidate(request)
    form = ResumeUploadForm(request.POST, request.FILES)
    if form.is_valid():
        make_primary = not candidate.resumes.exists()
        resume = Resume.objects.create(
            candidate=candidate,
            file=form.cleaned_data["file"],
            filename=form.cleaned_data["filename"] or form.cleaned_data["file"].name,
            is_primary=make_primary,
        )
        messages.success(request, "Resume uploaded.")
    else:
        messages.error(request, "Could not upload that file.")
    return redirect("applicant_dashboard")


@role_required("applicant")
def applications_list(request):
    candidate = _candidate(request)
    applications = (
        Application.objects.filter(candidate=candidate)
        .select_related("job__organization")
        .order_by("-applied_at")
    )
    stage = request.GET.get("stage")
    if stage:
        applications = applications.filter(stage=stage)

    context = {
        "active_nav": "applications",
        "applications": applications,
        "total_count": Application.objects.filter(candidate=candidate).count(),
        "stage_choices": Application.Stage.choices,
        "selected_stage": stage or "",
    }
    return render(request, "applicant/applications.html", context)


@role_required("applicant")
def interviews_list(request):
    candidate = _candidate(request)
    interviews = (
        Interview.objects.filter(application__candidate=candidate)
        .select_related("application__job__organization")
        .order_by("scheduled_at")
    )
    now = timezone.now()
    context = {
        "active_nav": "interviews",
        "upcoming": interviews.filter(scheduled_at__gte=now),
        "past": interviews.filter(scheduled_at__lt=now).order_by("-scheduled_at"),
    }
    return render(request, "applicant/interviews.html", context)


@role_required("applicant")
def skill_insights(request):
    candidate = _candidate(request)
    technical_skills = candidate.skills.filter(category=CandidateSkill.Category.TECHNICAL).select_related("skill")
    soft_skills = candidate.skills.filter(category=CandidateSkill.Category.SOFT).select_related("skill")

    gap_counts = {}
    matches = ResumeSkillMatch.objects.filter(analysis__resume__candidate=candidate).exclude(
        status=ResumeSkillMatch.MatchStatus.MATCHED
    ).select_related("skill")
    for match in matches:
        gap_counts[match.skill.name] = gap_counts.get(match.skill.name, 0) + 1
    worth_adding = sorted(gap_counts.items(), key=lambda pair: -pair[1])[:8]

    context = {
        "active_nav": "skills",
        "technical_skills": technical_skills,
        "soft_skills": soft_skills,
        "worth_adding": worth_adding,
    }
    return render(request, "applicant/skill_insights.html", context)


@role_required("applicant")
def notifications_list(request):
    notifications = list(
        Notification.objects.filter(recipient=request.user).select_related("sender", "application__job")
    )
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    context = {"active_nav": "notifications", "notifications": notifications}
    return render(request, "applicant/notifications.html", context)


@role_required("applicant")
def settings_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated.")
            return redirect("applicant_settings")
    else:
        form = PasswordChangeForm(request.user)

    context = {"active_nav": "settings", "form": form}
    return render(request, "applicant/settings.html", context)
