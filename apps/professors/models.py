"""Rate-my-professor: admin-managed professors + one rating per student.

Ratings show anonymously to students (admins see who) and are post-moderated —
they appear immediately and an admin can hide or delete any of them.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Professor(models.Model):
    name = models.CharField(max_length=120)
    title = models.CharField(
        max_length=120, blank=True, help_text="Field or role, e.g. Complex analysis."
    )
    photo_url = models.URLField(
        blank=True, help_text="Link to a photo (paste an image URL). Optional."
    )
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide without deleting."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProfessorRating(models.Model):
    professor = models.ForeignKey(
        Professor, on_delete=models.CASCADE, related_name="ratings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professor_ratings",
    )
    score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Any value from 0 to 5 (e.g. 3.5).",
    )
    comment = models.CharField(max_length=280, blank=True)
    is_approved = models.BooleanField(
        default=False,
        help_text="Shown publicly only after an admin approves it (pre-moderation).",
    )
    is_hidden = models.BooleanField(
        default=False, help_text="Hidden by an admin — excluded from the page and average."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_public(self):
        return self.is_approved and not self.is_hidden

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["professor", "user"], name="one_rating_per_professor"
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.professor}: {self.score}/5"
