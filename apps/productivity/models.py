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
    minutes = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField()

    class Meta:
        ordering = ["-completed_at"]
        indexes = [models.Index(fields=["user", "completed_at"])]

    def __str__(self):
        return f"{self.user} · {self.minutes}min"
