from django.db import models


class Resume(models.Model):
    candidate = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="resumes"
    )
    file = models.FileField(upload_to="resumes/")
    filename = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.filename or f"Resume #{self.pk}"


class ResumeAnalysis(models.Model):
    """AI match result for one resume against one job (resume-analysis.html)."""

    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="analyses")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="resume_analyses")

    overall_match_pct = models.PositiveSmallIntegerField()
    technical_skills_match_pct = models.PositiveSmallIntegerField()
    experience_relevancy_pct = models.PositiveSmallIntegerField()
    keyword_density_pct = models.PositiveSmallIntegerField()

    ai_insight = models.TextField(blank=True)
    similar_profiles_count = models.PositiveIntegerField(default=0)
    processing_time_seconds = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    engine_version = models.CharField(max_length=20, blank=True)  # e.g. "v4.2.1"

    analyzed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-analyzed_at"]
        verbose_name_plural = "resume analyses"

    def __str__(self):
        return f"{self.resume} vs {self.job} — {self.overall_match_pct}%"


class ResumeSkillMatch(models.Model):
    class MatchStatus(models.TextChoices):
        MATCHED = "matched", "Matched"
        PARTIAL = "partial", "Partially matched"
        MISSING = "missing", "Missing"

    analysis = models.ForeignKey(ResumeAnalysis, on_delete=models.CASCADE, related_name="skill_matches")
    skill = models.ForeignKey("taxonomy.Skill", on_delete=models.CASCADE, related_name="resume_matches")
    status = models.CharField(max_length=10, choices=MatchStatus.choices)

    class Meta:
        unique_together = ("analysis", "skill")


class OptimizationSuggestion(models.Model):
    class Impact(models.TextChoices):
        HIGH = "high", "High impact"
        MEDIUM = "medium", "Medium impact"
        LOW = "low", "Low impact"

    analysis = models.ForeignKey(ResumeAnalysis, on_delete=models.CASCADE, related_name="suggestions")
    title = models.CharField(max_length=150)  # e.g. "Add missing keywords"
    description = models.TextField()
    impact = models.CharField(max_length=10, choices=Impact.choices)
    is_addressed = models.BooleanField(default=False)

    def __str__(self):
        return self.title
