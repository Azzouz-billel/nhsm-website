"""Admin-managed content that isn't owned by another app: the site-wide news
bulletin shown in the footer ticker, and the daily traffic stats the owner
dashboard reads."""

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


class DailyStats(models.Model):
    """One row per day of site traffic, filled by the analytics middleware's
    end-of-day rollover (see config.middleware.AnalyticsMiddleware).

    Approximate by design: a "visitor" is a session (or an IP for session-less
    guests), and time-on-site is first-to-last request per visitor, capped —
    good enough to see trends without any third-party tracker.
    """

    date = models.DateField(unique=True)
    visitors = models.PositiveIntegerField(default=0)
    page_views = models.PositiveIntegerField(default=0)
    total_time_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date}: {self.visitors} visitors"
