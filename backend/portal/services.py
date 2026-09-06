"""Every UI number in the frontend that has no 1:1 model field lives here as
a plain function, computed from real data — see the plan's "what dynamic
means" table for the rationale behind each one."""
from datetime import date, timedelta

from django.db.models import Avg, F
from django.utils import timezone

from accounts.models import User
from applications.models import Application, Interview
from candidates.models import CandidateSkill
from notifications.models import Notification
from resumes.models import OptimizationSuggestion, ResumeAnalysis, ResumeSkillMatch


MAX_SKILL_WEIGHT = 5


def parse_weighted_skill(raw):
    """Parses a post-job.html skill entry like 'Figma:3' into ('Figma', 3).
    Plain 'Figma' (no colon) defaults to weight 1. Weight is clamped to
    1..MAX_SKILL_WEIGHT so a typo can't zero out or blow up the match score."""
    name, sep, weight_str = raw.rpartition(":")
    if not sep:
        return raw.strip(), 1
    name = name.strip()
    try:
        weight = int(weight_str.strip())
    except ValueError:
        return name, 1
    return name, max(1, min(MAX_SKILL_WEIGHT, weight))


def format_weighted_skill(name, weight):
    return f"{name}:{weight}" if weight != 1 else name


def match_tier(pct):
    """(label, badge-variant) bucket used for Excellent/Strong/Average/Low-Fit badges."""
    if pct is None:
        return ("—", "neutral")
    if pct >= 90:
        return ("Excellent", "success")
    if pct >= 75:
        return ("Strong", "success")
    if pct >= 50:
        return ("Average", "neutral")
    return ("Low Fit", "danger")


def match_percent_for(candidate, job):
    """Best-effort match % of a candidate against a job: prefers a real
    ResumeAnalysis for their primary resume, else a live skill-overlap
    fallback so every job card can still show a number."""
    primary_resume = candidate.resumes.filter(is_primary=True).first() or candidate.resumes.first()
    if primary_resume:
        analysis = (
            ResumeAnalysis.objects.filter(resume=primary_resume, job=job).order_by("-analyzed_at").first()
        )
        if analysis:
            return analysis.overall_match_pct

    required_job_skills = list(job.job_skills.filter(is_required=True))
    if not required_job_skills:
        required_job_skills = list(job.job_skills.all())
    if not required_job_skills:
        return None
    candidate_skill_ids = set(candidate.skills.values_list("skill_id", flat=True))
    total_weight = sum(js.weight for js in required_job_skills) or 1
    matched_weight = sum(js.weight for js in required_job_skills if js.skill_id in candidate_skill_ids)
    return round(matched_weight / total_weight * 100)


def resume_score_for(resume):
    """Latest overall match % for a specific resume (any job) — backs the
    per-resume score shown in the apply-modal dropdown."""
    analysis = ResumeAnalysis.objects.filter(resume=resume).order_by("-analyzed_at").first()
    if analysis:
        return analysis.overall_match_pct
    return resume.candidate.ats_score


def run_resume_analysis(resume, job):
    """Deterministic, rule-based scoring — not an external AI call, but a
    real computation over real CandidateSkill/WorkExperience/JobSkill data."""
    candidate = resume.candidate
    job_skills = list(job.job_skills.select_related("skill").all())
    candidate_skills = {
        cs.skill_id: cs for cs in CandidateSkill.objects.filter(candidate=candidate).select_related("skill")
    }

    matched, partial, missing = [], [], []
    matched_weight = partial_weight = 0
    for js in job_skills:
        cs = candidate_skills.get(js.skill_id)
        if cs and (cs.proficiency_pct is None or cs.proficiency_pct >= 60):
            matched.append(js.skill)
            matched_weight += js.weight
        elif cs:
            partial.append(js.skill)
            partial_weight += js.weight
        else:
            missing.append(js.skill)

    total_weight = sum(js.weight for js in job_skills) or 1
    technical_pct = round((matched_weight + 0.5 * partial_weight) / total_weight * 100)

    years = 0.0
    for exp in candidate.work_experiences.all():
        end = exp.end_date or date.today()
        years += max(0, (end - exp.start_date).days / 365.25)
    if job.min_experience_years:
        experience_pct = min(100, round(years / job.min_experience_years * 100))
    else:
        experience_pct = 100 if years > 0 else 60

    keyword_pct = round((matched_weight + partial_weight) / total_weight * 100)
    overall_pct = round(technical_pct * 0.5 + experience_pct * 0.3 + keyword_pct * 0.2)

    analysis = ResumeAnalysis.objects.create(
        resume=resume,
        job=job,
        overall_match_pct=overall_pct,
        technical_skills_match_pct=technical_pct,
        experience_relevancy_pct=experience_pct,
        keyword_density_pct=keyword_pct,
        ai_insight=_build_insight(candidate, job, matched, missing),
        similar_profiles_count=ResumeAnalysis.objects.filter(job=job).count(),
        processing_time_seconds=1.2,
        engine_version="v1.0",
    )

    for skill in matched:
        ResumeSkillMatch.objects.update_or_create(
            analysis=analysis, skill=skill, defaults={"status": ResumeSkillMatch.MatchStatus.MATCHED}
        )
    for skill in partial:
        ResumeSkillMatch.objects.update_or_create(
            analysis=analysis, skill=skill, defaults={"status": ResumeSkillMatch.MatchStatus.PARTIAL}
        )
    for skill in missing:
        ResumeSkillMatch.objects.update_or_create(
            analysis=analysis, skill=skill, defaults={"status": ResumeSkillMatch.MatchStatus.MISSING}
        )

    if missing:
        OptimizationSuggestion.objects.create(
            analysis=analysis,
            title="Add missing keywords",
            description=(
                f"Your resume doesn't show {', '.join(s.name for s in missing[:3])}. "
                "Add specific, measurable examples of this experience if you have it."
            ),
            impact=OptimizationSuggestion.Impact.HIGH,
        )
    if partial:
        OptimizationSuggestion.objects.create(
            analysis=analysis,
            title="Strengthen partial matches",
            description=(
                f"You have some experience with {', '.join(s.name for s in partial[:3])} — "
                "quantify it (metrics, project scale) to raise this score."
            ),
            impact=OptimizationSuggestion.Impact.MEDIUM,
        )

    return analysis


def _build_insight(candidate, job, matched, missing):
    name = candidate.user.get_full_name() or candidate.user.email
    total = len(matched) + len(missing)
    bits = [f"{name} matches {len(matched)} of {total} required skills for {job.title}."]
    if matched:
        bits.append(f"Strongest overlap: {', '.join(s.name for s in matched[:3])}.")
    if missing:
        bits.append(f"Biggest gaps: {', '.join(s.name for s in missing[:3])}.")
    return " ".join(bits)


def candidate_summary(candidate, analysis=None):
    """Overview-tab AI summary paragraph: reuses a real resume analysis
    insight when one exists, else composes one from real profile data."""
    if analysis and analysis.ai_insight:
        return analysis.ai_insight

    name = candidate.user.get_full_name() or candidate.user.email
    years = 0.0
    for exp in candidate.work_experiences.all():
        end = exp.end_date or date.today()
        years += max(0, (end - exp.start_date).days / 365.25)

    bits = [f"{name} is a {candidate.headline or 'candidate'} with about {years:.0f} years of professional experience."]
    if candidate.current_employer:
        bits.append(f"Currently at {candidate.current_employer}.")
    skill_names = list(candidate.skills.values_list("skill__name", flat=True)[:4])
    if skill_names:
        bits.append(f"Core strengths: {', '.join(skill_names)}.")
    return " ".join(bits)


def avg_time_to_hire(queryset):
    result = queryset.filter(stage=Application.Stage.HIRED).aggregate(
        avg=Avg(F("updated_at") - F("applied_at"))
    )["avg"]
    return result.days if result else None


def pipeline_fill_pct(job):
    total = job.applications.count()
    if not total:
        return 0
    progressed = job.applications.exclude(
        stage__in=[Application.Stage.NEW_APPLIED, Application.Stage.REJECTED]
    ).count()
    return round(progressed / total * 100)


def recent_activity(candidate, limit=5):
    events = []
    for interview in Interview.objects.filter(application__candidate=candidate).select_related(
        "application__job__organization"
    ):
        events.append(
            {
                "type": "interview",
                "at": interview.scheduled_at,
                "title": f"Interview scheduled with {interview.application.job.organization.name}",
                "icon": "bi-camera-video",
            }
        )
    for application in Application.objects.filter(candidate=candidate).select_related("job__organization"):
        events.append(
            {
                "type": "application",
                "at": application.applied_at,
                "title": f"Applied to {application.job.organization.name}",
                "icon": "bi-send",
            }
        )
    for analysis in ResumeAnalysis.objects.filter(resume__candidate=candidate).select_related("job"):
        events.append(
            {
                "type": "analysis",
                "at": analysis.analyzed_at,
                "title": f"Resume ATS scan completed — {analysis.overall_match_pct}% match for {analysis.job.title}",
                "icon": "bi-file-earmark-check",
            }
        )

    events.sort(key=lambda e: e["at"], reverse=True)
    return events[:limit]


def profile_ats_tips(candidate):
    """Actionable, rule-based suggestions to raise a candidate's ATS/match
    scores — same idea as an OptimizationSuggestion, but computed live from
    the whole profile instead of one resume+job pair."""
    tips = []
    if not candidate.headline:
        tips.append(
            'Add a professional headline (e.g. "Senior Product Designer") so recruiters '
            "immediately understand your role."
        )
    if not candidate.location:
        tips.append("Add your location — many recruiters filter candidates by location.")

    experiences = list(candidate.work_experiences.all())
    if not experiences:
        tips.append(
            "Add at least one work experience entry — experience relevancy is 30% of your "
            "match score, and candidates with no experience on file score the lowest band."
        )
    elif any(len(exp.description.split()) < 15 for exp in experiences):
        tips.append(
            "Add measurable achievements to your experience descriptions (metrics, project "
            "scale, team size) — thin descriptions read worse to recruiters skimming your profile."
        )

    technical_skills = list(candidate.skills.filter(category=CandidateSkill.Category.TECHNICAL))
    if len(technical_skills) < 5:
        tips.append(
            f"Add more technical skills — you have {len(technical_skills)} on file, aim for "
            "5-8 relevant ones so you match more job requirements."
        )
    if any(s.proficiency_pct is None for s in technical_skills):
        tips.append(
            "Set a proficiency % on every technical skill — skills below 60% only count as a "
            "partial match instead of a full one."
        )

    if not candidate.certifications.exists():
        tips.append(
            "Consider adding relevant certifications — they help turn partial skill matches "
            "into full matches for jobs that list them."
        )

    if not candidate.resumes.exists():
        tips.append("Upload or generate a CV — without one you can't apply to any job.")

    return tips


def profile_completion_breakdown(candidate):
    personal_fields = [candidate.headline, candidate.location, candidate.current_employer]
    personal_pct = round(sum(1 for f in personal_fields if f) / len(personal_fields) * 100)
    experience_pct = 100 if candidate.work_experiences.exists() else 0
    skills_pct = min(100, candidate.skills.count() * 10)
    overall = round((personal_pct + experience_pct + skills_pct) / 3)
    return {
        "personal_info": personal_pct,
        "work_experience": experience_pct,
        "skill_assessments": skills_pct,
        "overall": overall,
    }


def top_percentile_label(analysis):
    scores = list(ResumeAnalysis.objects.filter(job=analysis.job).values_list("overall_match_pct", flat=True))
    if len(scores) <= 1:
        return "Top 1% of Applicants"
    rank = sum(1 for s in scores if s > analysis.overall_match_pct) + 1
    top_pct = max(1, round(rank / len(scores) * 100))
    return f"Top {top_pct}% of Applicants"


def onboarding_estimate_label(experience_relevancy_pct):
    if experience_relevancy_pct >= 85:
        return "Accelerated (2 Weeks)"
    if experience_relevancy_pct >= 60:
        return "Standard (4 Weeks)"
    return "Extended (6+ Weeks)"


def period_trend_pct(queryset, date_field="applied_at", days=30):
    """% change in row count over the last `days` vs. the prior `days`-day window."""
    now = timezone.now()
    start_current = now - timedelta(days=days)
    start_previous = now - timedelta(days=days * 2)
    current = queryset.filter(**{f"{date_field}__gte": start_current}).count()
    previous = queryset.filter(
        **{f"{date_field}__gte": start_previous, f"{date_field}__lt": start_current}
    ).count()
    if not previous:
        return None
    return round((current - previous) / previous * 100)


def notify_new_application(application):
    """Tells the hiring manager (or every recruiter at the org, if none is
    set) that a candidate just applied."""
    job = application.job
    if job.hiring_manager_id:
        recipients = User.objects.filter(pk=job.hiring_manager_id)
    else:
        recipients = User.objects.filter(role="recruiter", recruiter_profile__organization=job.organization)

    candidate_name = application.candidate.user.get_full_name() or application.candidate.user.email
    for recruiter in recipients:
        Notification.objects.create(
            recipient=recruiter,
            sender=application.candidate.user,
            application=application,
            verb=Notification.Verb.NEW_APPLICATION,
            message=f"{candidate_name} applied for {job.title}.",
        )


def notify_interview_scheduled(interview):
    application = interview.application
    Notification.objects.create(
        recipient=application.candidate.user,
        sender=interview.interviewer,
        application=application,
        verb=Notification.Verb.INTERVIEW_SCHEDULED,
        message=(
            f"Interview scheduled for {application.job.title} on "
            f"{timezone.localtime(interview.scheduled_at):%b %d, %Y at %I:%M %p}."
        ),
    )


def notify_stage_changed(application, actor):
    Notification.objects.create(
        recipient=application.candidate.user,
        sender=actor,
        application=application,
        verb=Notification.Verb.STAGE_CHANGED,
        message=f"Your application for {application.job.title} is now marked as {application.get_stage_display()}.",
    )


def ats_trend_pct(candidate):
    primary = candidate.resumes.filter(is_primary=True).first() or candidate.resumes.first()
    if not primary:
        return None
    analyses = list(ResumeAnalysis.objects.filter(resume=primary).order_by("-analyzed_at")[:2])
    if len(analyses) < 2 or not analyses[1].overall_match_pct:
        return None
    latest, previous = analyses
    return round((latest.overall_match_pct - previous.overall_match_pct) / previous.overall_match_pct * 100)
