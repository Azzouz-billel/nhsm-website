"""Request/upvote board: students ask for missing resources; others upvote."""

from django.conf import settings
from django.db import models


class RequestStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    FULFILLED = "fulfilled", "Fulfilled"


class ResourceRequest(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resource_requests",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.ForeignKey(
        "resources.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
    )
    status = models.CharField(
        max_length=20, choices=RequestStatus.choices, default=RequestStatus.OPEN
    )
    fulfilled_link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class RequestVote(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="request_votes"
    )
    request = models.ForeignKey(
        ResourceRequest, on_delete=models.CASCADE, related_name="votes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "request"], name="unique_user_request_vote"
            )
        ]

    def __str__(self):
        return f"{self.user} ▲ {self.request}"
