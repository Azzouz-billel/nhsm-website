from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import Role
from apps.administration.forms import SubjectAdminForm
from apps.administration.models import Bulletin
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


class OwnerControlTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("owner", "o@x.dz", "x")
        self.admin = User.objects.create_user("adm", password="x", role=Role.ADMIN)
        self.other_admin = User.objects.create_user("adm2", password="x", role=Role.ADMIN)
        self.student = User.objects.create_user("stud", password="x")

    def test_admin_cannot_edit_the_owner(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(f"/manage/users/{self.owner.pk}/").status_code, 403
        )

    def test_admin_cannot_edit_another_admin(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(f"/manage/users/{self.other_admin.pk}/").status_code, 403
        )

    def test_admin_can_still_edit_a_student(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(f"/manage/users/{self.student.pk}/").status_code, 200
        )

    def test_owner_can_edit_an_admin(self):
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.get(f"/manage/users/{self.admin.pk}/").status_code, 200
        )

    def test_admin_cannot_promote_to_admin(self):
        self.client.force_login(self.admin)
        self.client.post(
            f"/manage/users/{self.student.pk}/",
            {"role": Role.ADMIN, "academic_group": "", "is_active": "on"},
        )
        self.student.refresh_from_db()
        self.assertNotEqual(self.student.role, Role.ADMIN)

    def test_owner_can_promote_to_admin(self):
        self.client.force_login(self.owner)
        self.client.post(
            f"/manage/users/{self.student.pk}/",
            {"role": Role.ADMIN, "academic_group": "", "is_active": "on"},
        )
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, Role.ADMIN)

    def test_role_form_hides_admin_choice_from_admins(self):
        from apps.administration.forms import UserRoleForm

        values = [v for v, _ in UserRoleForm(editor=self.admin).fields["role"].choices]
        self.assertNotIn(Role.ADMIN, values)

    def test_role_form_offers_admin_choice_to_owner(self):
        from apps.administration.forms import UserRoleForm

        values = [v for v, _ in UserRoleForm(editor=self.owner).fields["role"].choices]
        self.assertIn(Role.ADMIN, values)


class AnonymityRevealTests(TestCase):
    def setUp(self):
        from apps.productivity.models import StudySession
        from django.utils import timezone

        self.owner = User.objects.create_superuser("owner", "o@x.dz", "x")
        self.viewer = User.objects.create_user("viewer", password="x")
        self.anon = User.objects.create_user(
            "anon", password="x", display_name="RealName", is_anonymous_on_board=True
        )
        now = timezone.now()
        StudySession.objects.create(
            user=self.anon, minutes=30, started_at=now, completed_at=now
        )

    def test_leaderboard_hides_name_from_normal_viewer(self):
        self.client.force_login(self.viewer)
        rows = self.client.get("/api/leaderboard").json()["rows"]
        names = [r["name"] for r in rows]
        self.assertIn("Anonymous", names)
        self.assertNotIn("RealName", names)

    def test_leaderboard_reveals_name_to_owner(self):
        self.client.force_login(self.owner)
        rows = self.client.get("/api/leaderboard").json()["rows"]
        self.assertIn("RealName", [r["name"] for r in rows])

    def test_request_board_reveals_author_to_owner(self):
        from apps.requests.models import ResourceRequest

        ResourceRequest.objects.create(author=self.anon, title="Need TD")
        self.client.force_login(self.owner)
        response = self.client.get("/requests/")
        self.assertContains(response, "RealName")

    def test_request_board_hides_author_from_normal_viewer(self):
        from apps.requests.models import ResourceRequest

        ResourceRequest.objects.create(author=self.anon, title="Need TD")
        self.client.force_login(self.viewer)
        response = self.client.get("/requests/")
        self.assertNotContains(response, "RealName")


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


class BulletinModelTests(TestCase):
    def test_bulletin_requires_at_least_one_language(self):
        with self.assertRaises(ValidationError):
            Bulletin(text_en="", text_ar="").full_clean()

    def test_bulletin_with_one_language_is_valid(self):
        self.assertIsNone(Bulletin(text_en="Registration opens Monday").full_clean())


class BulletinTickerTests(TestCase):
    def test_active_bulletin_shows_in_bar(self):
        Bulletin.objects.create(text_en="Exams start June 1", is_active=True)
        response = self.client.get("/")
        self.assertContains(response, "Exams start June 1")

    def test_inactive_bulletin_is_hidden(self):
        Bulletin.objects.create(text_en="Hidden notice", is_active=False)
        response = self.client.get("/")
        self.assertNotContains(response, "Hidden notice")

    def test_arabic_text_renders_rtl(self):
        Bulletin.objects.create(text_ar="التسجيل يفتح الإثنين", is_active=True)
        response = self.client.get("/")
        self.assertContains(response, 'dir="rtl"')


class BulletinAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("adminuser", password="x", role=Role.ADMIN)
        self.student = User.objects.create_user("stud", password="x")

    def test_admin_can_create_bulletin(self):
        self.client.force_login(self.admin)
        self.client.post(
            "/manage/bulletins/new/",
            {"text_en": "New notice", "text_ar": "", "link": "", "order": 0, "is_active": "on"},
        )
        self.assertTrue(Bulletin.objects.filter(text_en="New notice").exists())

    def test_non_admin_cannot_reach_bulletins(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get("/manage/bulletins/").status_code, 302)

    def test_admin_can_delete_bulletin(self):
        self.client.force_login(self.admin)
        b = Bulletin.objects.create(text_en="Disposable")
        self.client.post(f"/manage/bulletins/{b.pk}/delete/")
        self.assertFalse(Bulletin.objects.filter(pk=b.pk).exists())
