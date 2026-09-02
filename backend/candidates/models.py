from django.db import models


class WorkExperience(models.Model):
    candidate = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="work_experiences"
    )
    title = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # null = current role
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-start_date"]

    def __str__(self):
        return f"{self.title} @ {self.company}"


class Education(models.Model):
    candidate = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="education"
    )
    degree = models.CharField(max_length=150)  # e.g. "BFA, Interaction Design"
    institution = models.CharField(max_length=150)
    start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-end_year"]

    def __str__(self):
        return f"{self.degree} — {self.institution}"


class CandidateSkill(models.Model):
    class Category(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        SOFT = "soft", "Soft"

    candidate = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="skills"
    )
    skill = models.ForeignKey("taxonomy.Skill", on_delete=models.CASCADE, related_name="candidate_skills")
    category = models.CharField(max_length=10, choices=Category.choices)
    proficiency_pct = models.PositiveSmallIntegerField(null=True, blank=True)  # technical skills only

    class Meta:
        unique_together = ("candidate", "skill")

    def __str__(self):
        return f"{self.candidate} — {self.skill}"


class Certification(models.Model):
    candidate = models.ForeignKey(
        "accounts.ApplicantProfile", on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=150)  # e.g. "NN/g UX Certification"

    def __str__(self):
        return self.name
