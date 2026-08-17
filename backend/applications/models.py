from django.conf import settings
from django.db import models


class Application(models.Model):
    """A candidate applying to a job — the central join entity for the whole pipeline."""

    class Stage(models.TextChoices):
        NEW_APPLIED = "new_applied", "New Applied"
        SCREENING = "screening", "Screening"
        REVIEW = "review", "Review"
        TECHNICAL_TEST = "technical_test", "Technical Test"
        INTERVIEW = "interview", "Interview"
        SHORTLISTED = "shortlisted", "Shortlisted"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"

    class Source(models.TextChoices):
        CAREERS_PAGE = "careers_page", "Careers page"
        LINKEDIN = "linkedin", "LinkedIn"
        REFERRAL = "referral", "Referral"
        IMPORT = "import", "Bulk import"

    candidate = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="applications"
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="applications")
    resume = models.ForeignKey(
        "resumes.Resume", on_delete=models.SET_NULL, null=True, blank=True, related_name="applications"
    )

    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW_APPLIED)
    ats_score = models.PositiveSmallIntegerField(null=True, blank=True)
    match_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, blank=True)

    note_to_hiring_team = models.TextField(blank=True)
    consent_given = models.BooleanField(default=False)

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("candidate", "job")
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.candidate} → {self.job} ({self.stage})"


class Note(models.Model):
    """Recruiter note on a candidate (candidate-profile.html Notes tab)."""

    candidate = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="notes"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="authored_notes"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note by {self.author} on {self.candidate}"


class Interview(models.Model):
    class Mode(models.TextChoices):
        VIDEO = "video", "Video"
        IN_PERSON = "in_person", "In person"
        PANEL = "panel", "Panel"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interviews_conducted",
    )
    scheduled_at = models.DateTimeField()
    mode = models.CharField(max_length=10, choices=Mode.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED)
    meeting_link = models.URLField(blank=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"Interview — {self.application} @ {self.scheduled_at:%Y-%m-%d %H:%M}"
