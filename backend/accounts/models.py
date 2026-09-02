from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Base identity for both personas. role decides which profile is attached."""

    class Role(models.TextChoices):
        RECRUITER = "recruiter", "Recruiter"
        APPLICANT = "applicant", "Applicant"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    avatar = models.ImageField(upload_to="avatars/", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class RecruiterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="recruiter_profile")
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="recruiters"
    )
    title = models.CharField(max_length=120, blank=True)  # e.g. "Head of Talent"

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.organization}"


class ApplicantProfile(models.Model):
    """The 'Candidate' entity. One per applicant user."""

    class Source(models.TextChoices):
        CAREERS_PAGE = "careers_page", "Careers page"
        LINKEDIN = "linkedin", "LinkedIn"
        REFERRAL = "referral", "Referral"
        IMPORT = "import", "Bulk import"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="applicant_profile")
    headline = models.CharField(max_length=150, blank=True)  # current title, e.g. "Senior Product Designer"
    current_employer = models.CharField(max_length=150, blank=True)
    location = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, blank=True)

    # Cached/denormalized values surfaced on dashboards; recomputed as resumes/applications change.
    ats_score = models.PositiveSmallIntegerField(default=0)
    profile_completion_pct = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.user.get_full_name() or self.user.email


class RecruiterGoal(models.Model):
    """Backs the 'Recruiter Goal' progress card on the dashboard."""

    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE, related_name="goals")
    period_start = models.DateField()
    period_end = models.DateField()
    target_hires = models.PositiveSmallIntegerField()
    current_hires = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"{self.recruiter} — {self.current_hires}/{self.target_hires} hires"
