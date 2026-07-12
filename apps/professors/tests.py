from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import Role

from .models import Professor, ProfessorRating

User = get_user_model()


def _rating(prof, user, score=4, tags=None, approved=True):
    return ProfessorRating.objects.create(
        professor=prof, user=user, score=score, tags=tags or [], is_approved=approved
    )


class RatingModelTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.user = User.objects.create_user("alice", password="x")

    def test_one_rating_per_user_per_professor(self):
        _rating(self.prof, self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            _rating(self.prof, self.user, score=2)


class AccessTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")

    def test_list_requires_login(self):
        self.assertEqual(self.client.get("/professors/").status_code, 302)

    def test_detail_requires_login(self):
        self.assertEqual(self.client.get(f"/professors/{self.prof.pk}/").status_code, 302)


class RateViewTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.student = User.objects.create_user("alice", password="x")

    def _post(self, score, tags=None, **kwargs):
        data = {"score": score, "hp_url": ""}
        if tags:
            data["tags"] = tags
        return self.client.post(f"/professors/{self.prof.pk}/rate/", data, **kwargs)

    def test_rating_requires_login(self):
        self._post(4)
        self.assertEqual(ProfessorRating.objects.count(), 0)

    def test_submitted_rating_is_pending(self):
        self.client.force_login(self.student)
        self._post(4, tags=["clear"])
        rating = ProfessorRating.objects.get(professor=self.prof, user=self.student)
        self.assertFalse(rating.is_approved)

    def test_submit_shows_thank_you(self):
        self.client.force_login(self.student)
        response = self._post(4, follow=True)
        self.assertContains(response, "submitted")

    def test_saves_selected_tags(self):
        self.client.force_login(self.student)
        self._post(4, tags=["clear", "fair"])
        rating = ProfessorRating.objects.get(professor=self.prof, user=self.student)
        self.assertEqual(sorted(rating.tags), ["clear", "fair"])

    def test_rejects_more_than_three_tags(self):
        self.client.force_login(self.student)
        self._post(4, tags=["clear", "fair", "patient", "engaging"])
        self.assertEqual(ProfessorRating.objects.count(), 0)

    def test_edit_updates_and_returns_to_pending(self):
        self.client.force_login(self.student)
        rating = _rating(self.prof, self.student, score=5, approved=True)
        self._post(2)
        rating.refresh_from_db()
        self.assertEqual(rating.score, 2)
        self.assertFalse(rating.is_approved)

    def test_accepts_decimal_score(self):
        self.client.force_login(self.student)
        self._post("3.5")
        rating = ProfessorRating.objects.get(professor=self.prof, user=self.student)
        self.assertEqual(float(rating.score), 3.5)

    def test_rejects_score_above_five(self):
        self.client.force_login(self.student)
        self._post("6")
        self.assertEqual(ProfessorRating.objects.count(), 0)

    def test_honeypot_blocks_rating(self):
        self.client.force_login(self.student)
        self.client.post(
            f"/professors/{self.prof.pk}/rate/",
            {"score": 4, "hp_url": "http://bot"},
        )
        self.assertEqual(ProfessorRating.objects.count(), 0)


class VisibilityTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.client.force_login(self.bob)

    def test_approved_rating_tag_shows(self):
        _rating(self.prof, self.alice, tags=["clear"], approved=True)
        response = self.client.get(f"/professors/{self.prof.pk}/")
        self.assertContains(response, '<span class="rating-tag">Clear explanations</span>')

    def test_pending_excluded_from_average(self):
        _rating(self.prof, self.alice, score=5, approved=False)
        response = self.client.get(f"/professors/{self.prof.pk}/")
        self.assertContains(response, "No ratings yet")

    def test_pending_tag_not_shown_to_others(self):
        _rating(self.prof, self.alice, tags=["tough"], approved=False)
        response = self.client.get(f"/professors/{self.prof.pk}/")
        self.assertNotContains(response, '<span class="rating-tag">Tough grader</span>')


class AnonymityTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.alice = User.objects.create_user("alice", password="x")
        self.bob = User.objects.create_user("bob", password="x")
        self.admin = User.objects.create_user("adm", password="x", role=Role.ADMIN)
        _rating(self.prof, self.alice, tags=["clear"], approved=True)

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

    def test_admin_can_approve(self):
        rating = _rating(self.prof, self.alice, approved=False)
        self.client.force_login(self.admin)
        self.client.post(f"/professors/ratings/{rating.pk}/approve/")
        rating.refresh_from_db()
        self.assertTrue(rating.is_approved)

    def test_admin_can_hide_approved(self):
        rating = _rating(self.prof, self.alice, approved=True)
        self.client.force_login(self.admin)
        self.client.post(f"/professors/ratings/{rating.pk}/hide/")
        rating.refresh_from_db()
        self.assertTrue(rating.is_hidden)

    def test_hidden_rating_excluded_from_page(self):
        rating = _rating(self.prof, self.alice, tags=["tough"], approved=True)
        rating.is_hidden = True
        rating.save()
        bob = User.objects.create_user("bob", password="x")
        self.client.force_login(bob)
        response = self.client.get(f"/professors/{self.prof.pk}/")
        self.assertNotContains(response, '<span class="rating-tag">Tough grader</span>')

    def test_author_can_delete_own_rating(self):
        rating = _rating(self.prof, self.alice, approved=False)
        self.client.force_login(self.alice)
        self.client.post(f"/professors/ratings/{rating.pk}/delete/")
        self.assertFalse(ProfessorRating.objects.filter(pk=rating.pk).exists())

    def test_other_student_cannot_delete(self):
        rating = _rating(self.prof, self.alice, approved=True)
        bob = User.objects.create_user("bob", password="x")
        self.client.force_login(bob)
        response = self.client.post(f"/professors/ratings/{rating.pk}/delete/")
        self.assertEqual(response.status_code, 403)


class ReviewQueueTests(TestCase):
    def setUp(self):
        self.prof = Professor.objects.create(name="Dr. Zemirni")
        self.alice = User.objects.create_user("alice", password="x")
        self.admin = User.objects.create_user("adm", password="x", role=Role.ADMIN)

    def test_admin_sees_pending_tags_in_queue(self):
        _rating(self.prof, self.alice, tags=["clear"], approved=False)
        self.client.force_login(self.admin)
        response = self.client.get("/manage/reviews/")
        self.assertContains(response, "Clear explanations")

    def test_non_admin_blocked_from_queue(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get("/manage/reviews/").status_code, 302)


class DisclaimerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="x")
        self.client.force_login(self.user)

    def test_disclaimer_on_list(self):
        response = self.client.get("/professors/")
        self.assertContains(response, "not statements of fact")

    def test_disclaimer_on_detail(self):
        prof = Professor.objects.create(name="Dr. X")
        response = self.client.get(f"/professors/{prof.pk}/")
        self.assertContains(response, "not statements of fact")


class AdminProfessorTests(TestCase):
    def test_admin_can_add_professor_with_photo_url(self):
        admin = User.objects.create_user("adm", password="x", role=Role.ADMIN)
        self.client.force_login(admin)
        self.client.post(
            "/manage/professors/new/",
            {
                "name": "Dr. Zaimi",
                "title": "Number theory",
                "photo_url": "https://example.com/zaimi.jpg",
                "is_active": "on",
            },
        )
        prof = Professor.objects.get(name="Dr. Zaimi")
        self.assertEqual(prof.photo_url, "https://example.com/zaimi.jpg")

    def test_non_admin_cannot_reach_manage_professors(self):
        student = User.objects.create_user("stud", password="x")
        self.client.force_login(student)
        self.assertEqual(self.client.get("/manage/professors/").status_code, 302)
