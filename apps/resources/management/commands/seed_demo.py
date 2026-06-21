"""Populate the database with demo subjects and resources.

    python manage.py seed_demo            # add demo data (idempotent)
    python manage.py seed_demo --reset    # wipe resources/subjects first

Drive links are placeholders — replace them with real Google Drive URLs.
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.productivity.models import StudySession
from apps.requests.models import RequestStatus, RequestVote, ResourceRequest
from apps.resources.models import (
    ExamPaper,
    ExamType,
    Resource,
    ResourceStatus,
    ResourceType,
    Subject,
)

# Subjects grouped by semester (early NHSM modules).
SUBJECTS = {
    1: ["Analyse 1", "Algèbre 1", "Algorithmique 1", "Logique mathématique"],
    2: ["Analyse 2", "Algèbre 2", "Algorithmique 2", "Physique 1"],
    3: ["Analyse 3", "Probabilités", "Topologie", "Structures de données"],
    4: ["Analyse complexe", "Statistiques", "Optimisation", "Bases de données"],
}

# (type, title suffix) pairs created for every subject.
RESOURCE_TEMPLATE = [
    (ResourceType.COURSE, "Cours complet"),
    (ResourceType.TD, "Série de TD"),
    (ResourceType.TP, "TP"),
    (ResourceType.SUMMARY, "Résumé"),
]

DEMO_LINK = "https://drive.google.com/drive/folders/DEMO-PLACEHOLDER"

# (year, exam type, has corrigé) papers created for every subject.
EXAM_TEMPLATE = [
    (2024, ExamType.EMD1, True),
    (2024, ExamType.EMD2, False),
    (2023, ExamType.EMD1, True),
    (2023, ExamType.RATTRAPAGE, False),
]

# (name, academic_group, streak) — streak doubles as "days with study sessions".
DEMO_STUDENTS = [
    ("Yacine", "first_cycle", 7),
    ("Imene", "first_cycle", 3),
    ("Sofiane", "second_year", 9),
    ("Nour", "second_year", 5),
    ("Walid", "third_year", 2),
    ("Maya", "third_year", 6),
    ("Rania", "fourth_data_science", 11),
    ("Bilal", "fourth_cryptology", 4),
    ("Aya", "fourth_modeling", 8),
    ("Karim", "fifth_year", 1),
]
ANONYMOUS_DEMO = {"Imene", "Bilal"}  # show as "Anonymous" on the board
DEMO_PASSWORD = "demo12345"

# (title, author name, status, number of upvotes to add)
DEMO_REQUESTS = [
    ("TD 3 corrigé for Analyse 2", "Yacine", RequestStatus.OPEN, 9),
    ("Past EMD2 papers for Probabilités", "Sofiane", RequestStatus.OPEN, 7),
    ("Full lecture notes for Topologie", "Maya", RequestStatus.IN_PROGRESS, 6),
    ("Optimisation exercises with corrections", "Rania", RequestStatus.OPEN, 5),
    ("Python TP solutions — Algorithmique 1", "Imene", RequestStatus.FULFILLED, 4),
    ("Summary sheet for Algèbre 2", "Nour", RequestStatus.OPEN, 3),
]


class Command(BaseCommand):
    help = "Seed demo subjects and resources for the resource library."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing resources and subjects before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            ResourceRequest.objects.all().delete()
            demo_usernames = [name.lower() for name, _, _ in DEMO_STUDENTS]
            get_user_model().objects.filter(username__in=demo_usernames).delete()
            deleted_e = ExamPaper.objects.all().delete()[0]
            deleted_r = Resource.objects.all().delete()[0]
            deleted_s = Subject.objects.all().delete()[0]
            self.stdout.write(
                self.style.WARNING(
                    f"Reset: removed {deleted_e} exam papers, {deleted_r} resources, "
                    f"{deleted_s} subjects and demo students."
                )
            )

        subjects_created = 0
        resources_created = 0
        exams_created = 0

        for semester, names in SUBJECTS.items():
            for name in names:
                subject, made = Subject.objects.get_or_create(
                    name=name,
                    semester=semester,
                    defaults={"description": f"{name} — semester {semester}."},
                )
                subjects_created += int(made)

                for index, (rtype, suffix) in enumerate(RESOURCE_TEMPLATE):
                    # Leave one TP per subject pending to demonstrate the queue.
                    status = (
                        ResourceStatus.PENDING
                        if rtype == ResourceType.TP and index % 2 == 0
                        else ResourceStatus.APPROVED
                    )
                    _, made = Resource.objects.get_or_create(
                        title=f"{name} — {suffix}",
                        subject=subject,
                        defaults={
                            "resource_type": rtype,
                            "drive_link": DEMO_LINK,
                            "status": status,
                            "description": f"{suffix} for {name}.",
                        },
                    )
                    resources_created += int(made)

                for year, exam_type, has_solution in EXAM_TEMPLATE:
                    label = ExamType(exam_type).label
                    _, made = ExamPaper.objects.get_or_create(
                        title=f"{name} — {label} {year}",
                        subject=subject,
                        year=year,
                        exam_type=exam_type,
                        defaults={
                            "drive_link": DEMO_LINK,
                            "has_solution": has_solution,
                            "solution_link": DEMO_LINK if has_solution else "",
                        },
                    )
                    exams_created += int(made)

        users_created, sessions_created = self._seed_students()
        requests_created = self._seed_requests()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {subjects_created} subjects, {resources_created} resources, "
                f"{exams_created} exam papers, {users_created} demo students, "
                f"{sessions_created} study sessions and {requests_created} requests."
            )
        )

    def _seed_students(self):
        """Create demo students with study sessions so the leaderboard is populated."""
        subjects = list(Subject.objects.all())
        if not subjects:
            return 0, 0

        User = get_user_model()
        now = timezone.now()
        today = timezone.localdate()
        users_created = 0
        sessions_created = 0

        for name, group, streak in DEMO_STUDENTS:
            user, made = User.objects.get_or_create(
                username=name.lower(),
                defaults={
                    "academic_group": group,
                    "display_name": name,
                    "is_anonymous_on_board": name in ANONYMOUS_DEMO,
                },
            )
            if not made:
                continue
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
            users_created += 1

            rng = random.Random(name)
            total = 0
            for day in range(streak):  # one streak day per consecutive past day
                for _ in range(rng.randint(1, 2)):
                    minutes = rng.choice([25, 30, 45, 50])
                    completed = now - timedelta(days=day, hours=rng.randint(0, 6))
                    StudySession.objects.create(
                        user=user,
                        subject=rng.choice(subjects),
                        minutes=minutes,
                        started_at=completed - timedelta(minutes=minutes),
                        completed_at=completed,
                    )
                    total += minutes
                    sessions_created += 1

            stats = user.stats
            stats.total_study_minutes = total
            stats.total_sessions = user.study_sessions.count()
            stats.current_streak = streak
            stats.longest_streak = streak
            stats.last_study_date = today
            stats.save()

        return users_created, sessions_created

    def _seed_requests(self):
        """Create demo resource requests with upvotes from the demo students."""
        User = get_user_model()
        voters = list(
            User.objects.filter(
                username__in=[name.lower() for name, _, _ in DEMO_STUDENTS]
            )
        )
        if not voters:
            return 0

        subjects = list(Subject.objects.all())
        created = 0
        for title, author_name, status, target_votes in DEMO_REQUESTS:
            author = User.objects.filter(username=author_name.lower()).first()
            subject = next(
                (s for s in subjects if s.name.lower() in title.lower()), None
            )
            req, made = ResourceRequest.objects.get_or_create(
                title=title,
                defaults={
                    "author": author,
                    "subject": subject,
                    "status": status,
                    "fulfilled_link": DEMO_LINK if status == RequestStatus.FULFILLED else "",
                    "description": "Requested by students — please share if you have it.",
                },
            )
            if not made:
                continue
            created += 1

            pool = [u for u in voters if u != author]
            random.Random(title).shuffle(pool)
            for voter in pool[:target_votes]:
                RequestVote.objects.get_or_create(user=voter, request=req)

        return created
