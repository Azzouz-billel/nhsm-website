from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (
    ExamPaper,
    ExamType,
    Resource,
    ResourceStatus,
    ResourceType,
    Speciality,
    Subject,
)

User = get_user_model()

SEARCH_URL = "/api/resources/search"
EXAM_SEARCH_URL = "/api/exams/search"


class ResourceSearchTests(TestCase):
    def setUp(self):
        self.analyse = Subject.objects.create(name="Analyse 1", semester=1)
        self.algebre = Subject.objects.create(name="Algèbre 2", semester=2)
        Resource.objects.create(
            title="Analyse 1 Cours",
            subject=self.analyse,
            resource_type=ResourceType.COURSE,
            drive_link="https://drive.google.com/x",
            status=ResourceStatus.APPROVED,
        )
        Resource.objects.create(
            title="Algèbre 2 TD",
            subject=self.algebre,
            resource_type=ResourceType.TD,
            drive_link="https://drive.google.com/y",
            status=ResourceStatus.APPROVED,
        )
        Resource.objects.create(
            title="Pending upload",
            subject=self.analyse,
            resource_type=ResourceType.COURSE,
            drive_link="https://drive.google.com/z",
            status=ResourceStatus.PENDING,
        )

    def test_excludes_non_approved_resources(self):
        response = self.client.get(SEARCH_URL)
        self.assertEqual(response.json()["count"], 2)

    def test_filters_by_semester(self):
        response = self.client.get(SEARCH_URL, {"semester": 2})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Algèbre 2 TD"])

    def test_filters_by_type(self):
        response = self.client.get(SEARCH_URL, {"type": ResourceType.TD})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Algèbre 2 TD"])

    def test_filters_by_text_query(self):
        response = self.client.get(SEARCH_URL, {"q": "algèbre"})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Algèbre 2 TD"])


class ResourceApprovalTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Topologie", semester=3)
        self.uploader = User.objects.create_user(username="contributor", password="x")
        self.resource = Resource.objects.create(
            title="Topologie Cours",
            subject=self.subject,
            drive_link="https://drive.google.com/t",
            status=ResourceStatus.PENDING,
            uploader=self.uploader,
        )

    def test_approve_sets_status_to_approved(self):
        self.resource.approve()
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.status, ResourceStatus.APPROVED)

    def test_approve_updates_uploader_contribution_count(self):
        self.resource.approve()
        self.assertEqual(self.uploader.stats.contributions, 1)


class ExamSearchTests(TestCase):
    def setUp(self):
        self.analyse = Subject.objects.create(name="Analyse 1", semester=1)
        self.algebre = Subject.objects.create(name="Algèbre 2", semester=2)
        ExamPaper.objects.create(
            title="Analyse 1 EMD1 2024",
            subject=self.analyse,
            year=2024,
            exam_type=ExamType.EMD1,
            drive_link="https://drive.google.com/a",
            has_solution=True,
        )
        ExamPaper.objects.create(
            title="Algèbre 2 Rattrapage 2023",
            subject=self.algebre,
            year=2023,
            exam_type=ExamType.RATTRAPAGE,
            drive_link="https://drive.google.com/b",
            has_solution=False,
        )

    def test_returns_all_exam_papers(self):
        response = self.client.get(EXAM_SEARCH_URL)
        self.assertEqual(response.json()["count"], 2)

    def test_filters_by_year(self):
        response = self.client.get(EXAM_SEARCH_URL, {"year": 2024})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Analyse 1 EMD1 2024"])

    def test_filters_by_solution_available(self):
        response = self.client.get(EXAM_SEARCH_URL, {"solution": "1"})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Analyse 1 EMD1 2024"])


class ExamSpecialityFilterTests(TestCase):
    def setUp(self):
        crypto = Subject.objects.create(
            name="Cryptographie", semester=7, speciality=Speciality.CRYPTOLOGY
        )
        modeling = Subject.objects.create(
            name="Modélisation", semester=7, speciality=Speciality.MODELING
        )
        ExamPaper.objects.create(
            title="Crypto EMD1",
            subject=crypto,
            year=2024,
            exam_type=ExamType.EMD1,
            drive_link="https://drive.google.com/crypto",
        )
        ExamPaper.objects.create(
            title="Modeling EMD1",
            subject=modeling,
            year=2024,
            exam_type=ExamType.EMD1,
            drive_link="https://drive.google.com/modeling",
        )

    def test_filters_exams_by_speciality(self):
        response = self.client.get(EXAM_SEARCH_URL, {"speciality": "cryptology"})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Crypto EMD1"])


class ResourceUploadTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)
        self.user = User.objects.create_user(username="uploader", password="x")
        self.payload = {
            "title": "My lecture notes",
            "subject": self.subject.pk,
            "resource_type": ResourceType.COURSE,
            "drive_link": "https://drive.google.com/n",
            "description": "",
        }

    def test_upload_creates_pending_resource(self):
        self.client.force_login(self.user)
        self.client.post("/resources/upload/", self.payload)
        self.assertEqual(
            Resource.objects.get(title="My lecture notes").status,
            ResourceStatus.PENDING,
        )

    def test_upload_sets_uploader_to_current_user(self):
        self.client.force_login(self.user)
        self.client.post("/resources/upload/", self.payload)
        self.assertEqual(
            Resource.objects.get(title="My lecture notes").uploader_id, self.user.pk
        )

    def test_anonymous_upload_is_redirected(self):
        response = self.client.post("/resources/upload/", self.payload)
        self.assertEqual(response.status_code, 302)


class SubjectValidationTests(TestCase):
    def test_advanced_subject_requires_speciality(self):
        subject = Subject(name="Cryptographie Avancée", semester=7)
        with self.assertRaises(ValidationError):
            subject.full_clean()

    def test_common_core_subject_rejects_speciality(self):
        subject = Subject(name="Analyse 1", semester=3, speciality=Speciality.MODELING)
        with self.assertRaises(ValidationError):
            subject.full_clean()

    def test_advanced_subject_with_speciality_is_valid(self):
        subject = Subject(name="Modélisation", semester=8, speciality=Speciality.MODELING)
        self.assertIsNone(subject.full_clean())


class ResourceSpecialityFilterTests(TestCase):
    def setUp(self):
        crypto = Subject.objects.create(
            name="Cryptographie", semester=7, speciality=Speciality.CRYPTOLOGY
        )
        modeling = Subject.objects.create(
            name="Modélisation", semester=7, speciality=Speciality.MODELING
        )
        Resource.objects.create(
            title="Crypto Cours", subject=crypto, resource_type=ResourceType.COURSE,
            drive_link="https://drive.google.com/c", status=ResourceStatus.APPROVED,
        )
        Resource.objects.create(
            title="Modeling Cours", subject=modeling, resource_type=ResourceType.COURSE,
            drive_link="https://drive.google.com/m", status=ResourceStatus.APPROVED,
        )

    def test_filters_resources_by_speciality(self):
        response = self.client.get(SEARCH_URL, {"speciality": "cryptology"})
        titles = [r["title"] for r in response.json()["results"]]
        self.assertEqual(titles, ["Crypto Cours"])


class SpecialityFilterRenderTests(TestCase):
    def test_library_page_renders_speciality_filter(self):
        response = self.client.get(reverse("resource_library"))
        self.assertContains(response, "Cryptology")

    def test_annales_page_renders_speciality_filter(self):
        response = self.client.get(reverse("annales"))
        self.assertContains(response, "Data Science")


class FooterSocialLinksTests(TestCase):
    def test_footer_links_to_github_profile(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "https://github.com/Azzouz-billel")


class AnnalesExamTypeTests(TestCase):
    def test_annales_page_offers_final_exam_type(self):
        response = self.client.get(reverse("annales"))
        self.assertContains(response, "Final exam")


class GoogleSiteVerificationTests(TestCase):
    def test_serves_verification_token_at_site_root(self):
        response = self.client.get("/googleb55567535a46ef21.html")
        self.assertContains(response, "google-site-verification: googleb55567535a46ef21.html")


class HealthCheckTests(TestCase):
    def test_healthz_returns_ok(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.content, b"ok")

    def test_healthz_makes_no_database_queries(self):
        with self.assertNumQueries(0):
            self.client.get("/healthz")


class IMMSpecialityTests(TestCase):
    def test_imm_is_a_valid_advanced_speciality(self):
        subject = Subject(name="IMM Module", semester=7, speciality=Speciality.IMM)
        self.assertIsNone(subject.full_clean())


class ResourceUploadLimitTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)

    def _data(self, **over):
        data = {
            "title": "ok title",
            "subject": self.subject.pk,
            "resource_type": ResourceType.COURSE,
            "drive_link": "https://drive.google.com/x",
            "description": "",
        }
        data.update(over)
        return data

    def test_rejects_title_over_70_chars(self):
        from apps.resources.forms import ResourceUploadForm
        form = ResourceUploadForm(data=self._data(title="x" * 71))
        self.assertFalse(form.is_valid())

    def test_rejects_description_over_70_chars(self):
        from apps.resources.forms import ResourceUploadForm
        form = ResourceUploadForm(data=self._data(description="x" * 71))
        self.assertFalse(form.is_valid())


class AnnalesModuleSemesterAttrTests(TestCase):
    def test_annales_module_options_carry_semester(self):
        subject = Subject.objects.create(name="Analyse 1", semester=1)
        ExamPaper.objects.create(
            title="A1 EMD1", subject=subject, year=2024,
            exam_type=ExamType.EMD1, drive_link="https://drive.google.com/a",
        )
        response = self.client.get(reverse("annales"))
        self.assertContains(response, 'data-semester="1"')


class ContactPageTests(TestCase):
    def test_contact_page_shows_creator_and_collaborators(self):
        response = self.client.get(reverse("contact"))
        self.assertContains(response, "Built with")


class DonationLinkTests(TestCase):
    def test_home_links_to_chargily_donation(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "pay.chargily.com/payment-links/01kwyrqtjam3xmf3p1s0wpzshm")


class HomeStatsTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)
        Resource.objects.create(title="R1", subject=self.subject,
            drive_link="https://drive.google.com/a", status=ResourceStatus.APPROVED)
        Resource.objects.create(title="R2", subject=self.subject,
            drive_link="https://drive.google.com/b", status=ResourceStatus.APPROVED)
        ExamPaper.objects.create(title="E1", subject=self.subject, year=2024,
            exam_type=ExamType.EMD1, drive_link="https://drive.google.com/c")

    def test_resource_count_includes_exams(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["resource_count"], 3)

    def test_home_uses_exams_label_not_annales(self):
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Annales")


class HomeHeroCtaTests(TestCase):
    def test_anonymous_sees_create_account(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Create Account")

    def test_signed_in_sees_my_account(self):
        self.client.force_login(User.objects.create_user(username="hero", password="x"))
        response = self.client.get(reverse("home"))
        self.assertContains(response, "See my account")


class SecurityHeadersTests(TestCase):
    def test_permissions_policy_header_present(self):
        response = self.client.get(reverse("home"))
        self.assertIn("Permissions-Policy", response)
