from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Role
from apps.moderation.models import GuestbookComment
from apps.resources.models import Resource, ResourceStatus, Subject

User = get_user_model()

QUEUE_URL = "/moderation/"


class ModerationAccessTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)
        self.resource = Resource.objects.create(
            title="Pending notes",
            subject=self.subject,
            drive_link="https://drive.google.com/x",
            status=ResourceStatus.PENDING,
        )
        self.approver = User.objects.create_user(
            username="approver", password="x", role=Role.APPROVER
        )
        self.student = User.objects.create_user(username="student", password="x")

    def test_student_is_redirected_from_queue(self):
        self.client.force_login(self.student)
        response = self.client.get(QUEUE_URL)
        self.assertEqual(response.status_code, 302)

    def test_approver_can_open_queue(self):
        self.client.force_login(self.approver)
        response = self.client.get(QUEUE_URL)
        self.assertEqual(response.status_code, 200)

    def test_approver_can_approve_resource(self):
        self.client.force_login(self.approver)
        self.client.post(
            f"/moderation/{self.resource.pk}/review/", {"action": "approve"}
        )
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.status, ResourceStatus.APPROVED)

    def test_student_cannot_approve_resource(self):
        self.client.force_login(self.student)
        self.client.post(
            f"/moderation/{self.resource.pk}/review/", {"action": "approve"}
        )
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.status, ResourceStatus.PENDING)


class GuestbookCommentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fan", password="x")

    def test_anonymous_cannot_comment(self):
        response = self.client.post("/comments/add/", {"text": "Great site!"})
        self.assertEqual(response.status_code, 302)  # bounced to login
        self.assertEqual(GuestbookComment.objects.count(), 0)

    def test_member_comment_is_created_unapproved(self):
        self.client.force_login(self.user)
        response = self.client.post("/comments/add/", {"text": "Love this hub!"})
        self.assertEqual(response.status_code, 302)
        comment = GuestbookComment.objects.get()
        self.assertEqual(comment.author, self.user)
        self.assertFalse(comment.is_approved)

    def test_empty_comment_is_rejected(self):
        self.client.force_login(self.user)
        self.client.post("/comments/add/", {"text": ""})
        self.assertEqual(GuestbookComment.objects.count(), 0)

    def test_only_approved_comments_show_on_home(self):
        GuestbookComment.objects.create(author=self.user, text="Hidden note")
        GuestbookComment.objects.create(
            author=self.user, text="Public note", is_approved=True
        )
        response = self.client.get("/")
        self.assertContains(response, "Public note")
        self.assertNotContains(response, "Hidden note")

    def test_comment_strips_html_tags_and_prevents_xss(self):
        self.client.force_login(self.user)
        self.client.post("/comments/add/", {"text": "<script>alert('xss')</script>Great site!"})
        comment = GuestbookComment.objects.get()
        self.assertNotIn("<script>", comment.text)
        self.assertIn("Great site!", comment.text)

    def test_parameter_tampering_is_ignored(self):
        self.client.force_login(self.user)
        self.client.post("/comments/add/", {"text": "Hacker note", "is_approved": "True", "is_pinned": "True"})
        comment = GuestbookComment.objects.get()
        self.assertFalse(comment.is_approved)
        self.assertFalse(comment.is_pinned)
