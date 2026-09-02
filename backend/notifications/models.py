from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Verb(models.TextChoices):
        NEW_APPLICATION = "new_application", "New application"
        STAGE_CHANGED = "stage_changed", "Stage changed"
        INTERVIEW_SCHEDULED = "interview_scheduled", "Interview scheduled"
        MESSAGE = "message", "Message"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    verb = models.CharField(max_length=30, choices=Verb.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_verb_display()} → {self.recipient}"
