from django.conf import settings
from django.db import models


class GuestbookComment(models.Model):
    """A member's note of encouragement, shown on the home page wall.

    Pre-moderated: nothing is public until an admin approves it from the
    manage area, so the owner keeps full control over what appears.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guestbook_comments",
    )
    text = models.CharField(max_length=280)
    is_approved = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return f"{self.author.username}: {self.text[:40]}"
