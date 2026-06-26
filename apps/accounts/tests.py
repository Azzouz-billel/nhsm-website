from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Role, ThemePreference

User = get_user_model()

REGISTER_URL = "/accounts/register/"
THEME_URL = "/accounts/theme/"

VALID = {
    "username": "newstudent",
    "password1": "Topology2026!",
    "password2": "Topology2026!",
    "email": "s@example.com",
    "academic_group": "",
    "display_name": "",
}


class RegistrationTests(TestCase):
    def test_registration_creates_student(self):
        self.client.post(REGISTER_URL, VALID)
        self.assertEqual(User.objects.get(username="newstudent").role, Role.STUDENT)


class ThemePreferenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="themer", password="x")

    def test_update_theme_persists_preference(self):
        self.client.force_login(self.user)
        self.client.post(THEME_URL, {"theme": ThemePreference.DARK})
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme_preference, ThemePreference.DARK)


class UserStatsSignalTests(TestCase):
    def test_creating_user_creates_stats(self):
        user = User.objects.create_user(username="fresh", password="x")
        self.assertEqual(user.stats.total_study_minutes, 0)
