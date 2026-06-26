from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.resources.models import Subject

from .models import RequestStatus, RequestVote, ResourceRequest

User = get_user_model()
BOARD_URL = "/requests/"


class VotingTests(TestCase):
    def setUp(self):
        self.req = ResourceRequest.objects.create(title="Need TD 2 corrigé")
        self.user = User.objects.create_user(username="voter", password="x")

    def test_vote_creates_a_vote(self):
        self.client.force_login(self.user)
        self.client.post(f"/requests/{self.req.pk}/vote/")
        self.assertEqual(RequestVote.objects.filter(request=self.req).count(), 1)

    def test_second_vote_toggles_it_off(self):
        self.client.force_login(self.user)
        self.client.post(f"/requests/{self.req.pk}/vote/")
        self.client.post(f"/requests/{self.req.pk}/vote/")
        self.assertEqual(RequestVote.objects.filter(request=self.req).count(), 0)

    def test_anonymous_vote_is_redirected(self):
        response = self.client.post(f"/requests/{self.req.pk}/vote/")
        self.assertEqual(response.status_code, 302)


class BoardSortTests(TestCase):
    def setUp(self):
        self.low = ResourceRequest.objects.create(title="Low")
        self.high = ResourceRequest.objects.create(title="High")
        voter = User.objects.create_user(username="voter", password="x")
        RequestVote.objects.create(user=voter, request=self.high)

    def test_board_lists_most_upvoted_first(self):
        response = self.client.get(BOARD_URL)
        titles = [r.title for r in response.context["requests"]]
        self.assertEqual(titles[0], "High")


class CreateTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Analyse 1", semester=1)
        self.user = User.objects.create_user(username="author", password="x")
        self.payload = {"title": "Need lecture notes", "subject": self.subject.pk, "description": ""}

    def test_authenticated_create_sets_author(self):
        self.client.force_login(self.user)
        self.client.post(BOARD_URL, self.payload)
        self.assertEqual(
            ResourceRequest.objects.get(title="Need lecture notes").author, self.user
        )

    def test_anonymous_create_is_redirected(self):
        response = self.client.post(BOARD_URL, self.payload)
        self.assertEqual(response.status_code, 302)


class StatusUpdateTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="x")
        self.other = User.objects.create_user(username="other", password="x")
        self.req = ResourceRequest.objects.create(title="A request", author=self.author)

    def test_author_can_fulfil_request(self):
        self.client.force_login(self.author)
        self.client.post(
            f"/requests/{self.req.pk}/status/",
            {"status": "fulfilled", "fulfilled_link": "https://drive.google.com/x"},
        )
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, RequestStatus.FULFILLED)

    def test_other_user_cannot_update_status(self):
        self.client.force_login(self.other)
        response = self.client.post(
            f"/requests/{self.req.pk}/status/", {"status": "fulfilled"}
        )
        self.assertEqual(response.status_code, 403)


class DeleteTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author", password="x")
        self.other = User.objects.create_user(username="other", password="x")
        self.admin = User.objects.create_user(username="boss", password="x", role="admin")
        self.req = ResourceRequest.objects.create(title="A request", author=self.author)

    def test_author_can_delete_request(self):
        self.client.force_login(self.author)
        self.client.post(f"/requests/{self.req.pk}/delete/")
        self.assertEqual(ResourceRequest.objects.filter(pk=self.req.pk).count(), 0)

    def test_admin_can_delete_request(self):
        self.client.force_login(self.admin)
        self.client.post(f"/requests/{self.req.pk}/delete/")
        self.assertEqual(ResourceRequest.objects.filter(pk=self.req.pk).count(), 0)

    def test_other_user_cannot_delete_request(self):
        self.client.force_login(self.other)
        response = self.client.post(f"/requests/{self.req.pk}/delete/")
        self.assertEqual(response.status_code, 403)
