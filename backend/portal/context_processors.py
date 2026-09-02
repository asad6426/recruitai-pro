def notifications_context(request):
    """Feeds the topbar bell icon's unread badge on every recruiter/applicant page."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    from notifications.models import Notification

    return {"unread_notifications_count": Notification.objects.filter(recipient=user, is_read=False).count()}


def search_quicklinks(request):
    """Feeds the global-search-modal quick-links list with real recent
    candidates/jobs instead of a few hardcoded names."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.role:
        return {}

    if user.role == "recruiter":
        from applications.models import Application

        org = user.recruiter_profile.organization
        return {
            "search_candidates": Application.objects.select_related("candidate__user", "job")
            .filter(job__organization=org)
            .order_by("-applied_at")[:5],
        }

    from jobs.models import Job

    return {
        "search_jobs": Job.objects.filter(status=Job.Status.OPEN).select_related("organization").order_by("-published_at")[:5],
    }
