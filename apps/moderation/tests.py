from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Role
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
