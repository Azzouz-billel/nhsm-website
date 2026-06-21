"""Custom user model and denormalised stats.

The user model carries the academic profile directly (rather than a separate
Profile table) to keep the data model simple for a small maintenance team.
``UserStats`` holds counters that would otherwise be expensive aggregates on
every leaderboard / profile page load.
"""

from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class AcademicGroup(models.TextChoices):
    """The cohort a student belongs to — used for leaderboard grouping.

    Single field rather than separate year/track because NHSM's structure is a
    single progression and the 4th-year tracks are mutually exclusive.
    """

    FIRST_CYCLE = "first_cycle", "First Cycle"
    SECOND_YEAR = "second_year", "Second Year"
    THIRD_YEAR = "third_year", "Third Year"
    FOURTH_MODELING = "fourth_modeling", "4th Year — Modeling"
    FOURTH_CRYPTOLOGY = "fourth_cryptology", "4th Year — Cryptology"
    FOURTH_DATA_SCIENCE = "fourth_data_science", "4th Year — Data Science"
    FIFTH_YEAR = "fifth_year", "Fifth Year"


class Role(models.TextChoices):
    STUDENT = "student", "Student"
    APPROVER = "approver", "Approver"
    ADMIN = "admin", "Admin"


class ThemePreference(models.TextChoices):
    SYSTEM = "system", "System"
    LIGHT = "light", "Light"
    DARK = "dark", "Dark"


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    academic_group = models.CharField(
        max_length=32, choices=AcademicGroup.choices, blank=True
    )
    display_name = models.CharField(
        max_length=60, blank=True, help_text="Shown on leaderboards instead of username."
    )
    is_anonymous_on_board = models.BooleanField(
        default=False, help_text="Hide identity on public leaderboards."
    )
    theme_preference = models.CharField(
        max_length=10, choices=ThemePreference.choices, default=ThemePreference.SYSTEM
    )

    @property
    def is_admin(self):
        """Full-power admin (or a Django superuser)."""
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_approver(self):
        """Can moderate. Admins and superusers inherit approver powers."""
        return self.role == Role.APPROVER or self.is_admin

    def board_name(self):
        """Name to show on public boards, honoring the anonymity flag."""
        if self.is_anonymous_on_board:
            return "Anonymous"
        return self.display_name or self.username


class UserStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="stats")
    total_study_minutes = models.PositiveIntegerField(default=0)
    total_sessions = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_study_date = models.DateField(null=True, blank=True)
    contributions = models.PositiveIntegerField(
        default=0, help_text="Number of approved resource uploads."
    )

    class Meta:
        verbose_name_plural = "user stats"

    def __str__(self):
        return f"Stats for {self.user}"

    def record_study(self, minutes, study_date):
        """Add a completed focus block and update the daily streak.

        Streak = consecutive days with at least one block. Studying again on a
        day already counted leaves the streak unchanged.
        """
        self.total_study_minutes += minutes
        self.total_sessions += 1
        if self.last_study_date == study_date:
            pass  # already counted today
        elif self.last_study_date == study_date - timedelta(days=1):
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.last_study_date = study_date
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.save()


@receiver(post_save, sender=User)
def create_user_stats(sender, instance, created, **kwargs):
    if created:
        UserStats.objects.create(user=instance)
