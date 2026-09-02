from django.conf import settings
from django.db import models


class Job(models.Model):
    class Department(models.TextChoices):
        DESIGN = "design", "Design"
        ENGINEERING = "engineering", "Engineering"
        DATA = "data", "Data"
        MARKETING = "marketing", "Marketing"
        PRODUCT = "product", "Product"
        OPERATIONS = "operations", "Operations"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"

    class Workplace(models.TextChoices):
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"
        ON_SITE = "on_site", "On-site"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="jobs"
    )
    hiring_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs_managed",
        limit_choices_to={"role": "recruiter"},
    )

    title = models.CharField(max_length=150)
    department = models.CharField(max_length=20, choices=Department.choices)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices)
    workplace = models.CharField(max_length=20, choices=Workplace.choices)
    location = models.CharField(max_length=120)
    salary_min = models.PositiveIntegerField()
    salary_max = models.PositiveIntegerField()

    summary = models.TextField(blank=True)  # "Role summary"
    min_experience_years = models.PositiveSmallIntegerField(default=0)
    team_name = models.CharField(max_length=100, blank=True)  # e.g. "Product Design"
    team_size = models.PositiveSmallIntegerField(null=True, blank=True)

    skills = models.ManyToManyField("taxonomy.Skill", through="JobSkill", related_name="jobs")

    # Screening
    auto_shortlist_threshold_pct = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Auto-shortlist candidates at/above this ATS score. Null = off."
    )
    auto_reject_threshold_pct = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Auto-reject candidates below this match %. Null = off."
    )
    anonymize_screening = models.BooleanField(default=True)

    # Publishing
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    publish_to_careers_page = models.BooleanField(default=True)
    publish_to_linkedin = models.BooleanField(default=True)
    publish_to_partner_boards = models.BooleanField(default=False)
    applications_close_at = models.DateField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} @ {self.organization}"


class JobSkill(models.Model):
    """Through table: a required/nice-to-have skill for a job, weighted for match scoring."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="job_skills")
    skill = models.ForeignKey("taxonomy.Skill", on_delete=models.CASCADE, related_name="job_skills")
    is_required = models.BooleanField(default=True)
    weight = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ("job", "skill")

    def __str__(self):
        return f"{self.job} — {self.skill}"


class JobRequirement(models.Model):
    """One line of the 'Requirements' textarea; also feeds the ATS keyword matcher."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="requirements")
    text = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class JobResponsibility(models.Model):
    """One line of the 'What you'll do' list on the job detail page."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="responsibilities")
    text = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class JobBenefit(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="benefits")
    text = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class SavedJob(models.Model):
    """Applicant's bookmarked jobs ('Saved Jobs (12)')."""

    applicant = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="saved_jobs"
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("applicant", "job")
        ordering = ["-saved_at"]
