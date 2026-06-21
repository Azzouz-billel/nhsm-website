from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.resources.models import Subject

from .models import StudySession

User = get_user_model()
SESSION_URL = "/api/study-sessions"
LEADERBOARD_URL = "/api/leaderboard"


class StreakTests(TestCase):
    def setUp(self):
        self.stats = User.objects.create_user(username="learner", password="x").stats

    def test_first_session_starts_streak_at_one(self):
        self.stats.record_study(25, date(2026, 6, 20))
        self.assertEqual(self.stats.current_streak, 1)

    def test_consecutive_day_increments_streak(self):
        self.stats.record_study(25, date(2026, 6, 20))
        self.stats.record_study(25, date(2026, 6, 21))
        self.assertEqual(self.stats.current_streak, 2)

    def test_same_day_does_not_increment_streak(self):
        self.stats.record_study(25, date(2026, 6, 20))
        self.stats.record_study(25, date(2026, 6, 20))
        self.assertEqual(self.stats.current_streak, 1)

    def test_gap_resets_streak(self):
        self.stats.record_study(25, date(2026, 6, 20))
        self.stats.record_study(25, date(2026, 6, 23))
        self.assertEqual(self.stats.current_streak, 1)

    def test_minutes_accumulate_across_sessions(self):
        self.stats.record_study(25, date(2026, 6, 20))
        self.stats.record_study(15, date(2026, 6, 20))
        self.assertEqual(self.stats.total_study_minutes, 40)


class StudySessionAPITests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)
        self.user = User.objects.create_user(username="learner", password="x")

    def test_anonymous_cannot_log_session(self):
        response = self.client.post(
            SESSION_URL, {"subject": self.subject.pk, "minutes": 25}
        )
        self.assertEqual(response.status_code, 403)

    def test_authenticated_session_creates_record(self):
        self.client.force_login(self.user)
        self.client.post(SESSION_URL, {"subject": self.subject.pk, "minutes": 25})
        self.assertEqual(StudySession.objects.filter(user=self.user).count(), 1)

    def test_authenticated_session_updates_total_minutes(self):
        self.client.force_login(self.user)
        self.client.post(SESSION_URL, {"subject": self.subject.pk, "minutes": 25})
        self.user.stats.refresh_from_db()
        self.assertEqual(self.user.stats.total_study_minutes, 25)

    def test_invalid_minutes_are_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            SESSION_URL, {"subject": self.subject.pk, "minutes": 999}
        )
        self.assertEqual(response.status_code, 400)


class LeaderboardTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)
        self.now = timezone.now()
        self.alice = self._student("alice", "second_year", "Alice", streak=2)
        self.bob = self._student("bob", "second_year", "Bob", streak=9)
        self.carol = self._student("carol", "third_year", "Carol", streak=4, anon=True)
        self._session(self.alice, 60, days_ago=0)
        self._session(self.alice, 100, days_ago=10)  # older — outside today/week
        self._session(self.bob, 30, days_ago=0)
        self._session(self.carol, 90, days_ago=0)

    def _student(self, username, group, display, streak, anon=False):
        user = User.objects.create_user(username=username, password="x")
        user.academic_group = group
        user.display_name = display
        user.is_anonymous_on_board = anon
        user.save()
        user.stats.current_streak = streak
        user.stats.save()
        return user

    def _session(self, user, minutes, days_ago):
        completed = self.now - timedelta(days=days_ago)
        StudySession.objects.create(
            user=user,
            subject=self.subject,
            minutes=minutes,
            started_at=completed - timedelta(minutes=minutes),
            completed_at=completed,
        )

    def test_global_all_time_ranks_by_minutes(self):
        rows = self.client.get(
            LEADERBOARD_URL, {"window": "all", "group": "global"}
        ).json()["rows"]
        self.assertEqual(rows[0]["name"], "Alice")  # 160 min total

    def test_group_filter_restricts_results(self):
        rows = self.client.get(LEADERBOARD_URL, {"group": "third_year"}).json()["rows"]
        self.assertEqual({r["group"] for r in rows}, {"Third Year"})

    def test_anonymous_user_name_is_hidden(self):
        rows = self.client.get(LEADERBOARD_URL, {"group": "third_year"}).json()["rows"]
        self.assertEqual(rows[0]["name"], "Anonymous")

    def test_today_window_excludes_old_sessions(self):
        rows = self.client.get(
            LEADERBOARD_URL, {"window": "today", "group": "second_year"}
        ).json()["rows"]
        alice = next(r for r in rows if r["name"] == "Alice")
        self.assertEqual(alice["minutes"], 60)

    def test_streak_sort_orders_by_streak(self):
        rows = self.client.get(
            LEADERBOARD_URL, {"group": "second_year", "sort": "streak"}
        ).json()["rows"]
        self.assertEqual(rows[0]["name"], "Bob")  # streak 9 beats Alice's 2
