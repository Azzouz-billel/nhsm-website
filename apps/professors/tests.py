from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Role

from .models import Professor, ProfessorRating

User = get_user_model()


class RatingModelTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.user = User.objects.create_user("alice", password="x")

    def test_one_rating_per_user_per_professor(self):
        ProfessorRating.objects.create(professor=self.prof, user=self.user, score=3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfessorRating.objects.create(professor=self.prof, user=self.user, score=4)


class RateViewTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.student = User.objects.create_user("alice", password="x")

    def _post(self, score, comment=""):
        return self.client.post(
            f"/professors/{self.prof.pk}/rate/",
            {"score": score, "comment": comment, "hp_url": ""},
        )

    def test_rating_requires_login(self):
        response = self._post(4)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProfessorRating.objects.count(), 0)

    def test_student_can_rate(self):
        self.client.force_login(self.student)
        self._post(4, "very clear")
        rating = ProfessorRating.objects.get(professor=self.prof, user=self.student)
        self.assertEqual(rating.score, 4)

    def test_second_rating_updates_not_duplicates(self):
        self.client.force_login(self.student)
        self._post(4)
        self._post(2)
        self.assertEqual(ProfessorRating.objects.filter(professor=self.prof).count(), 1)
        self.assertEqual(
            ProfessorRating.objects.get(professor=self.prof, user=self.student).score, 2
        )

    def test_honeypot_blocks_rating(self):
        self.client.force_login(self.student)
        self.client.post(
            f"/professors/{self.prof.pk}/rate/",
            {"score": 4, "comment": "spam", "hp_url": "http://bot"},
        )
        self.assertEqual(ProfessorRating.objects.count(), 0)


class AnonymityTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.admin = User.objects.create_user("adm", password="x", role=Role.ADMIN)
        ProfessorRating.objects.create(
            professor=self.prof, user=self.alice, score=5, comment="great teacher"
        )

    def test_normal_viewer_sees_anonymous_not_username(self):
        self.client.force_login(self.bob)
        response = self.client.get(f"/professors/{self.prof.pk}/")
        self.assertContains(response, "Anonymous")
        self.assertNotContains(response, "alice")

    def test_admin_sees_username(self):
        self.client.force_login(self.admin)
        response = self.client.get(f"/professors/{self.prof.pk}/")
        self.assertContains(response, "alice")


class ModerationTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.alice = User.objects.create_user("alice", password="x")
        self.admin = User.objects.create_user("adm", password="x", role=Role.ADMIN)
        self.rating = ProfessorRating.objects.create(
            professor=self.prof, user=self.alice, score=1, comment="hidden me"
        )

    def test_hidden_rating_excluded_from_average_and_page(self):
        self.rating.is_hidden = True
        self.rating.save()
        response = self.client.get(f"/professors/{self.prof.pk}/")
        self.assertNotContains(response, "hidden me")
        self.assertContains(response, "No ratings yet")

    def test_admin_can_hide(self):
        self.client.force_login(self.admin)
        self.client.post(f"/professors/ratings/{self.rating.pk}/hide/")
        self.rating.refresh_from_db()
        self.assertTrue(self.rating.is_hidden)

    def test_author_can_delete_own_rating(self):
        self.client.force_login(self.alice)
        self.client.post(f"/professors/ratings/{self.rating.pk}/delete/")
        self.assertFalse(ProfessorRating.objects.filter(pk=self.rating.pk).exists())

    def test_other_student_cannot_delete(self):
        bob = User.objects.create_user("bob", password="x")
        self.client.force_login(bob)
        response = self.client.post(f"/professors/ratings/{self.rating.pk}/delete/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ProfessorRating.objects.filter(pk=self.rating.pk).exists())


class AdminProfessorTests(TestCase):
    def test_admin_can_add_professor(self):
        admin = User.objects.create_user("adm", password="x", role=Role.ADMIN)
        self.client.force_login(admin)
        self.client.post(
            "/manage/professors/new/",
            {"name": "Dr. Zaimi", "title": "Number theory", "is_active": "on"},
        )
        self.assertTrue(Professor.objects.filter(name="Dr. Zaimi").exists())

    def test_non_admin_cannot_reach_manage_professors(self):
        student = User.objects.create_user("stud", password="x")
        self.client.force_login(student)
        self.assertEqual(self.client.get("/manage/professors/").status_code, 302)
