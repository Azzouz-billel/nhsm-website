from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import Role, ThemePreference

User = get_user_model()

REGISTER_URL = "/accounts/register/"
THEME_URL = "/accounts/theme/"
FORGOT_URL = "/accounts/forgot/"
CHANGE_PASSWORD_URL = "/accounts/password/"

VALID = {
    "username": "newstudent",
    "password1": "Topology2026!",
    "password2": "Topology2026!",
    "email": "s@example.com",
    "academic_group": "first_cycle",
    "display_name": "",
}


class RegistrationTests(TestCase):
    def test_registration_creates_student(self):
        self.client.post(REGISTER_URL, VALID)
        self.assertEqual(User.objects.get(username="newstudent").role, Role.STUDENT)

    def test_registration_requires_academic_group(self):
        data = dict(VALID, username="nogroup", academic_group="")
        self.client.post(REGISTER_URL, data)
        self.assertFalse(User.objects.filter(username="nogroup").exists())


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


class ProfileFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="profiler", password="x")

    def test_profile_page_has_no_file_upload(self):
        self.client.force_login(self.user)
        response = self.client.get("/accounts/profile/")
        self.assertNotContains(response, 'type="file"')


class UsernameLimitTests(TestCase):
    def test_registration_rejects_long_username(self):
        long_name = "x" * 31
        self.client.post(REGISTER_URL, dict(VALID, username=long_name))
        self.assertFalse(User.objects.filter(username=long_name).exists())


class RecoveryCodeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="forgetful", password="oldpass123!"
        )

    def _reset_payload(self, code, password="BrandNew123!"):
        return {
            "username": "forgetful",
            "recovery_code": code,
            "new_password1": password,
            "new_password2": password,
        }

    def test_registration_creates_recovery_code(self):
        self.client.post(REGISTER_URL, VALID)
        self.assertTrue(User.objects.get(username="newstudent").recovery_code)

    def test_wrong_code_keeps_password_and_is_generic(self):
        old_hash = self.user.password
        response = self.client.post(FORGOT_URL, self._reset_payload("AAAA-BBBB-CCCC"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, old_hash)
        self.assertContains(response, "Wrong username or recovery code", status_code=200)

    def test_unknown_username_gets_same_generic_error(self):
        payload = self._reset_payload(self.user.recovery_code)
        payload["username"] = "ghost"
        response = self.client.post(FORGOT_URL, payload)
        self.assertContains(response, "Wrong username or recovery code", status_code=200)

    def test_correct_code_resets_rotates_and_logs_in(self):
        old_code = self.user.recovery_code
        response = self.client.post(FORGOT_URL, self._reset_payload(old_code))
        self.assertRedirects(response, "/accounts/profile/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNew123!"))
        self.assertNotEqual(self.user.recovery_code, old_code)
        # The used code no longer works.
        self.client.logout()
        response = self.client.post(FORGOT_URL, self._reset_payload(old_code, "Other123!"))
        self.assertContains(response, "Wrong username or recovery code", status_code=200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNew123!"))

    def test_code_match_is_case_insensitive(self):
        response = self.client.post(
            FORGOT_URL, self._reset_payload(self.user.recovery_code.lower())
        )
        self.assertRedirects(response, "/accounts/profile/")


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="changer", password="Current123!"
        )

    def test_requires_login(self):
        response = self.client.get(CHANGE_PASSWORD_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_change_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            CHANGE_PASSWORD_URL,
            {
                "old_password": "Current123!",
                "new_password1": "Updated123!",
                "new_password2": "Updated123!",
            },
        )
        self.assertRedirects(response, "/accounts/profile/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Updated123!"))


@override_settings(RATELIMIT_ENABLED=True)
class RecoveryThrottleTests(TestCase):
    PAYLOAD = {
        "username": "throttle-victim",
        "recovery_code": "AAAA-BBBB-CCCC",
        "new_password1": "BrandNew123!",
        "new_password2": "BrandNew123!",
    }

    def test_forgot_is_throttled_after_limit(self):
        for _ in range(10):
            response = self.client.post(FORGOT_URL, self.PAYLOAD)
            self.assertEqual(response.status_code, 200)  # form error, but allowed
        response = self.client.post(FORGOT_URL, self.PAYLOAD)
        self.assertEqual(response.status_code, 429)

    def test_throttle_is_per_username(self):
        for _ in range(10):
            self.client.post(FORGOT_URL, self.PAYLOAD)
        other = dict(self.PAYLOAD, username="someone-else")
        response = self.client.post(FORGOT_URL, other)
        self.assertEqual(response.status_code, 200)


class AdminRegenerateCodeTests(TestCase):
    URL = "/manage/users/{pk}/recovery-code/"

    def setUp(self):
        self.student = User.objects.create_user(username="stu", password="x")
        self.admin = User.objects.create_user(
            username="boss", password="x", role=Role.ADMIN
        )

    def test_admin_regenerates_student_code(self):
        old_code = self.student.recovery_code
        self.client.force_login(self.admin)
        response = self.client.post(self.URL.format(pk=self.student.pk))
        self.assertRedirects(response, "/manage/users/")
        self.student.refresh_from_db()
        self.assertNotEqual(self.student.recovery_code, old_code)

    def test_student_is_rejected(self):
        old_code = self.student.recovery_code
        self.client.force_login(self.student)
        response = self.client.post(self.URL.format(pk=self.student.pk))
        self.assertEqual(response.status_code, 302)  # redirected to login
        self.student.refresh_from_db()
        self.assertEqual(self.student.recovery_code, old_code)

    def test_admin_cannot_reset_another_admins_code(self):
        other_admin = User.objects.create_user(
            username="boss2", password="x", role=Role.ADMIN
        )
        old_code = other_admin.recovery_code
        self.client.force_login(self.admin)
        response = self.client.post(self.URL.format(pk=other_admin.pk))
        self.assertEqual(response.status_code, 403)
        other_admin.refresh_from_db()
        self.assertEqual(other_admin.recovery_code, old_code)


class RegistrationHoneypotTests(TestCase):
    def test_filled_honeypot_is_rejected(self):
        data = dict(VALID, username="botuser", hp_url="http://spam.example")
        self.client.post(REGISTER_URL, data)
        self.assertFalse(User.objects.filter(username="botuser").exists())


@override_settings(
    AXES_ENABLED=True,
    AUTHENTICATION_BACKENDS=[
        "axes.backends.AxesStandaloneBackend",
        "django.contrib.auth.backends.ModelBackend",
    ],
)
class AxesLockoutTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="victim", password="rightpass123")

    def test_repeated_bad_logins_are_locked(self):
        for _ in range(5):
            self.client.post("/accounts/login/", {"username": "victim", "password": "wrong"})
        response = self.client.post("/accounts/login/", {"username": "victim", "password": "wrong"})
        self.assertEqual(response.status_code, 429)
