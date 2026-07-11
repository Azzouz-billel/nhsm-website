"""Admin-managed content that isn't owned by another app — currently the
site-wide news bulletin shown in the footer ticker."""

from django.core.exceptions import ValidationError
from django.db import models


class Bulletin(models.Model):
    """One news line for the footer ticker. Bilingual: English and/or Arabic."""

    text_en = models.CharField(max_length=200, blank=True)
    text_ar = models.CharField(max_length=200, blank=True, verbose_name="Arabic text")
    link = models.URLField(blank=True, help_text="Optional link the item points to.")
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide without deleting."
    )
    order = models.PositiveSmallIntegerField(
        default=0, help_text="Lower numbers show first."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def clean(self):
        super().clean()
        if not self.text_en and not self.text_ar:
            raise ValidationError("Enter the news in at least one language.")

    def __str__(self):
        return self.text_en or self.text_ar
