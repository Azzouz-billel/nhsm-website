"""Resource library: the course-notes catalogue students filter and open.

Taxonomy is semester -> subject (module) -> resource. Resources carry a
pending -> approved -> rejected workflow; only approved resources are public.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Speciality(models.TextChoices):
    CRYPTOLOGY = "cryptology", "Cryptology"
    MODELING = "modeling", "Modeling"
    DATA_SCIENCE = "data_science", "Data Science"


class Subject(models.Model):
    """A module / course, scoped to a semester."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    semester = models.PositiveSmallIntegerField(help_text="1–10 across the five years.")
    description = models.CharField(max_length=255, blank=True)
    speciality = models.CharField(
        max_length=20,
        choices=Speciality.choices,
        blank=True,
        help_text="Required for S7–S10; leave blank for the S1–S6 common core.",
    )

    class Meta:
        ordering = ["semester", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "semester"], name="unique_subject_per_semester"
            )
        ]

    def __str__(self):
        return f"S{self.semester} · {self.name}"

    def clean(self):
        super().clean()
        if self.semester is None:
            return
        if self.semester >= 7 and not self.speciality:
            raise ValidationError(
                {"speciality": "Modules from S7 onward must have a speciality."}
            )
        if self.semester <= 6 and self.speciality:
            raise ValidationError(
                {"speciality": "S1–S6 modules are common core; leave speciality blank."}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-s{self.semester}")
        super().save(*args, **kwargs)


class ResourceType(models.TextChoices):
    COURSE = "course", "Cours"
    TD = "td", "TD"
    TP = "tp", "TP"
    SUMMARY = "summary", "Résumé"
    BOOK = "book", "Livre"
    OTHER = "other", "Autre"


class ResourceStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Resource(models.Model):
    title = models.CharField(max_length=200)
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="resources"
    )
    resource_type = models.CharField(
        max_length=20, choices=ResourceType.choices, default=ResourceType.COURSE
    )
    drive_link = models.URLField(help_text="Google Drive (or similar) link.")
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=ResourceStatus.choices, default=ResourceStatus.PENDING
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_resources",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_resources",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return self.title

    def approve(self, by_user=None):
        """Mark approved and refresh the uploader's denormalised contribution count."""
        self.status = ResourceStatus.APPROVED
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        self._sync_uploader_contributions()

    def reject(self, by_user=None):
        self.status = ResourceStatus.REJECTED
        self.reviewed_by = by_user
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        self._sync_uploader_contributions()

    def _sync_uploader_contributions(self):
        if not self.uploader_id:
            return
        stats = getattr(self.uploader, "stats", None)
        if stats is None:
            return
        stats.contributions = self.uploader.uploaded_resources.filter(
            status=ResourceStatus.APPROVED
        ).count()
        stats.save(update_fields=["contributions"])


class ExamType(models.TextChoices):
    EMD1 = "emd1", "EMD 1"
    EMD2 = "emd2", "EMD 2"
    RATTRAPAGE = "rattrapage", "Rattrapage"
    CONTROLE = "controle", "Contrôle continu"
    OTHER = "other", "Autre"


class ExamPaper(models.Model):
    """A past exam paper (sujet d'examen) — the Annales archive.

    Kept separate from ``Resource`` (course notes) but reusing ``Subject`` so the
    taxonomy (semester -> module) stays consistent. Admin-managed; publicly visible.
    """

    title = models.CharField(max_length=200)
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="exam_papers"
    )
    year = models.PositiveSmallIntegerField(help_text="Year the exam was given, e.g. 2024.")
    exam_type = models.CharField(
        max_length=20, choices=ExamType.choices, default=ExamType.EMD1
    )
    drive_link = models.URLField(help_text="Link to the exam paper (Google Drive).")
    has_solution = models.BooleanField(
        default=False, help_text="A corrigé (solution) is available."
    )
    solution_link = models.URLField(blank=True, help_text="Optional link to the corrigé.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "subject__semester", "title"]
        indexes = [models.Index(fields=["year"]), models.Index(fields=["exam_type"])]

    def __str__(self):
        return f"{self.title} ({self.year})"
