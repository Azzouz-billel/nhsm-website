from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import Role
from apps.administration.forms import SubjectAdminForm
from apps.resources.models import Resource, ResourceStatus, Subject

User = get_user_model()
DASHBOARD_URL = "/manage/"


class AdminAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("adminuser", password="x", role=Role.ADMIN)
        self.approver = User.objects.create_user("appr", password="x", role=Role.APPROVER)
        self.student = User.objects.create_user("stud", password="x")

    def test_admin_can_open_dashboard(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(DASHBOARD_URL).status_code, 200)

    def test_approver_is_blocked(self):
        self.client.force_login(self.approver)
        self.assertEqual(self.client.get(DASHBOARD_URL).status_code, 302)

    def test_student_is_blocked(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(DASHBOARD_URL).status_code, 302)

    def test_anonymous_is_blocked(self):
        self.assertEqual(self.client.get(DASHBOARD_URL).status_code, 302)


class AdminResourceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("adminuser", password="x", role=Role.ADMIN)
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)
        self.client.force_login(self.admin)

    def test_admin_created_resource_can_be_approved_immediately(self):
        self.client.post(
            "/manage/resources/new/",
            {
                "title": "Admin upload",
                "subject": self.subject.pk,
                "resource_type": "course",
                "drive_link": "https://drive.google.com/x",
                "description": "",
                "status": ResourceStatus.APPROVED,
            },
        )
        self.assertEqual(
            Resource.objects.get(title="Admin upload").status, ResourceStatus.APPROVED
        )

    def test_admin_can_delete_resource(self):
        resource = Resource.objects.create(
            title="Disposable",
            subject=self.subject,
            drive_link="https://drive.google.com/y",
            status=ResourceStatus.APPROVED,
        )
        self.client.post(f"/manage/resources/{resource.pk}/delete/")
        self.assertFalse(Resource.objects.filter(pk=resource.pk).exists())


class PromoteCommandTests(TestCase):
    def test_promote_user_sets_admin_role(self):
        user = User.objects.create_user("promo", password="x")
        call_command("promote_user", "promo", "admin")
        user.refresh_from_db()
        self.assertEqual(user.role, Role.ADMIN)


class UserRoleEditTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("adminuser", password="x", role=Role.ADMIN)
        self.target = User.objects.create_user("target", password="x")
        self.client.force_login(self.admin)

    def test_admin_can_change_user_role(self):
        self.client.post(
            f"/manage/users/{self.target.pk}/",
            {"role": Role.APPROVER, "academic_group": "", "is_active": "on"},
        )
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.APPROVER)


class SubjectAdminFormTests(TestCase):
    def test_rejects_advanced_subject_without_speciality(self):
        form = SubjectAdminForm(data={"name": "Crypto Avancée", "semester": 8, "description": ""})
        self.assertFalse(form.is_valid())

    def test_accepts_advanced_subject_with_speciality(self):
        form = SubjectAdminForm(
            data={"name": "Crypto Avancée", "semester": 8, "speciality": "cryptology", "description": ""}
        )
        self.assertTrue(form.is_valid())

    def test_rejects_common_core_subject_with_speciality(self):
        form = SubjectAdminForm(
            data={"name": "Analyse 1", "semester": 3, "speciality": "cryptology", "description": ""}
        )
        self.assertIn("speciality", form.errors)


class AdminFormLimitTests(TestCase):
    def test_subject_admin_form_rejects_long_name(self):
        from apps.administration.forms import SubjectAdminForm
        form = SubjectAdminForm(data={"name": "x" * 71, "semester": 1, "description": ""})
        self.assertFalse(form.is_valid())
