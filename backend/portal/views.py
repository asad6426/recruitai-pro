from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from candidates.models import CandidateSkill
from resumes.models import Resume


@login_required
def resume_print(request, resume_id):
    """Printable resume page — rendered live from the candidate's structured
    profile data, not a stored file. Viewable by the candidate themselves, or
    by a recruiter at an org the candidate has actually applied to."""
    resume = get_object_or_404(Resume.objects.select_related("candidate__user"), pk=resume_id)
    candidate = resume.candidate
    user = request.user

    is_owner = candidate.user_id == user.id
    is_reviewing_recruiter = (
        not is_owner
        and user.role == "recruiter"
        and resume.applications.filter(job__organization=user.recruiter_profile.organization).exists()
    )
    if not (is_owner or is_reviewing_recruiter):
        raise Http404

    context = {
        "resume": resume,
        "candidate": candidate,
        "is_owner": is_owner,
        "work_experiences": candidate.work_experiences.all(),
        "education": candidate.education.all(),
        "technical_skills": candidate.skills.filter(category=CandidateSkill.Category.TECHNICAL).select_related(
            "skill"
        ),
        "soft_skills": candidate.skills.filter(category=CandidateSkill.Category.SOFT).select_related("skill"),
        "certifications": candidate.certifications.all(),
    }
    return render(request, "resume_print.html", context)
