from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from candidates.models import CandidateSkill
from jobs.models import Job, JobPayment
from resumes.models import Resume

from . import sslcommerz


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


def _mark_paid(payment):
    """Confirms a payment with SSLCommerz server-to-server and, if genuine,
    marks it SUCCESS and publishes the job. Safe to call more than once for
    the same payment (success page + IPN can both land) — and always makes
    sure the job is actually published whenever the payment is SUCCESS,
    rather than assuming that only ever happened here before."""
    if payment.status != JobPayment.Status.SUCCESS:
        val_id = payment.val_id
        if not val_id:
            return False

        result = sslcommerz.validate_transaction(val_id)
        if result.get("status") not in ("VALID", "VALIDATED"):
            return False

        payment.status = JobPayment.Status.SUCCESS
        payment.gateway_response = result
        payment.save(update_fields=["status", "gateway_response", "updated_at"])

    job = payment.job
    if job.status != Job.Status.OPEN:
        job.status = Job.Status.OPEN
        if not job.published_at:
            job.published_at = timezone.now()
        job.save(update_fields=["status", "published_at"])
    return True


@csrf_exempt
@require_POST
def job_payment_success(request):
    """SSLCommerz redirects the recruiter's browser here (POST) after a
    successful checkout. Not login-gated — the request comes from
    SSLCommerz's domain, not an authenticated session."""
    tran_id = request.POST.get("tran_id")
    val_id = request.POST.get("val_id")
    payment = JobPayment.objects.filter(tran_id=tran_id).select_related("job").first()

    ok = False
    if payment:
        payment.val_id = val_id or payment.val_id
        payment.save(update_fields=["val_id", "updated_at"])
        ok = _mark_paid(payment)

    return render(request, "recruiter/payment_result.html", {"outcome": "success" if ok else "unverified", "payment": payment})


@csrf_exempt
@require_POST
def job_payment_fail(request):
    tran_id = request.POST.get("tran_id")
    payment = JobPayment.objects.filter(tran_id=tran_id).select_related("job").first()
    if payment and payment.status == JobPayment.Status.PENDING:
        payment.status = JobPayment.Status.FAILED
        payment.gateway_response = request.POST.dict()
        payment.save(update_fields=["status", "gateway_response", "updated_at"])
    return render(request, "recruiter/payment_result.html", {"outcome": "fail", "payment": payment})


@csrf_exempt
@require_POST
def job_payment_cancel(request):
    tran_id = request.POST.get("tran_id")
    payment = JobPayment.objects.filter(tran_id=tran_id).select_related("job").first()
    if payment and payment.status == JobPayment.Status.PENDING:
        payment.status = JobPayment.Status.CANCELLED
        payment.gateway_response = request.POST.dict()
        payment.save(update_fields=["status", "gateway_response", "updated_at"])
    return render(request, "recruiter/payment_result.html", {"outcome": "cancel", "payment": payment})


@csrf_exempt
@require_POST
def job_payment_ipn(request):
    """Server-to-server notification — the authoritative confirmation path.
    Only reachable when this app is deployed at a public URL (SSLCommerz's
    servers can't reach localhost), so job_payment_success also validates
    directly for local/dev testing. Always answers 200 so SSLCommerz doesn't
    keep retrying."""
    tran_id = request.POST.get("tran_id")
    val_id = request.POST.get("val_id")
    payment = JobPayment.objects.filter(tran_id=tran_id).first()
    if payment and val_id:
        payment.val_id = val_id
        payment.save(update_fields=["val_id", "updated_at"])
        _mark_paid(payment)
    return HttpResponse("OK")
