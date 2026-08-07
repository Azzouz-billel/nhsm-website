"""Pomodoro study tracking: one row per completed focus block."""

from django.conf import settings
from django.db import models


class StudySession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    subject = models.ForeignKey(
        "resources.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="study_sessions",
    )
    label = models.CharField(
        max_length=60,
        blank=True,
        help_text="Custom activity name when no module is picked (e.g. Revision).",
    )
    minutes = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField()

    class Meta:
        ordering = ["-completed_at"]
        indexes = [models.Index(fields=["user", "completed_at"])]

    def __str__(self):
        subject_or_label = self.subject or self.label or "Unspecified"
        return f"{self.user} · {subject_or_label} · {self.minutes}min"

