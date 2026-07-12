from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AcademicGroup
from apps.resources.models import Speciality, Subject

from .models import StudySession
from .serializers import StudySessionSerializer

User = get_user_model()

WINDOWS = {"today", "week", "semester", "all"}

# Which semesters (and, for 4th-year tracks, which speciality) each academic
# group studies. Used to scope the timer's module list to the user's own year.
_GROUP_SCOPE = {
    AcademicGroup.FIRST_CYCLE: ((1, 2), ""),
    AcademicGroup.SECOND_YEAR: ((3, 4), ""),
    AcademicGroup.THIRD_YEAR: ((5, 6), ""),
    AcademicGroup.FOURTH_MODELING: ((7, 8), Speciality.MODELING),
    AcademicGroup.FOURTH_CRYPTOLOGY: ((7, 8), Speciality.CRYPTOLOGY),
    AcademicGroup.FOURTH_DATA_SCIENCE: ((7, 8), Speciality.DATA_SCIENCE),
    AcademicGroup.FOURTH_IMM: ((7, 8), Speciality.IMM),
    AcademicGroup.FIFTH_YEAR: ((9, 10), ""),
}


def _subjects_for(user):
    """Timer modules scoped to the user's year (and track for 4th-years). A
    blank/unknown group — anonymous users or profiles not filled in — sees all."""
    subjects = Subject.objects.order_by("semester", "name")
    scope = _GROUP_SCOPE.get(user.academic_group) if user.is_authenticated else None
    if not scope:
        return subjects
    semesters, speciality = scope
    subjects = subjects.filter(semester__in=semesters)
    if speciality:
        subjects = subjects.filter(speciality=speciality)
    return subjects


def _subject_breakdown(user):
    return (
        StudySession.objects.filter(user=user)
        .values("subject__name")
        .annotate(total=Sum("minutes"))
        .order_by("-total")[:8]
    )


def timer(request):
    """Pomodoro timer. Anonymous users can run it; only signed-in time is logged."""
    context = {"subjects": _subjects_for(request.user)}
    if request.user.is_authenticated:
        today = timezone.localdate()
        context["stats"] = request.user.stats
        context["today_minutes"] = (
            StudySession.objects.filter(
                user=request.user, completed_at__date=today
            ).aggregate(total=Sum("minutes"))["total"]
            or 0
        )
        context["per_subject"] = _subject_breakdown(request.user)
    return render(request, "productivity/timer.html", context)


class StudySessionCreateAPIView(CreateAPIView):
    """Log one completed focus block and return the user's refreshed stats."""

    serializer_class = StudySessionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        minutes = serializer.validated_data["minutes"]
        subject = serializer.validated_data["subject"]

        now = timezone.now()
        StudySession.objects.create(
            user=request.user,
            subject=subject,
            minutes=minutes,
            started_at=now - timedelta(minutes=minutes),
            completed_at=now,
        )
        request.user.stats.record_study(minutes, timezone.localdate())

        stats = request.user.stats
        today_minutes = (
            StudySession.objects.filter(
                user=request.user, completed_at__date=timezone.localdate()
            ).aggregate(total=Sum("minutes"))["total"]
            or 0
        )
        return Response(
            {
                "total_study_minutes": stats.total_study_minutes,
                "total_sessions": stats.total_sessions,
                "current_streak": stats.current_streak,
                "today_minutes": today_minutes,
            },
            status=201,
        )


def _semester_start(today):
    """Approximate start of the current academic semester (autumn / spring)."""
    if today.month >= 9:
        return date(today.year, 9, 1)
    if today.month == 1:
        return date(today.year - 1, 9, 1)
    return date(today.year, 2, 1)


def _window_start(window, today):
    if window == "today":
        return today
    if window == "week":
        return today - timedelta(days=today.weekday())  # Monday
    if window == "semester":
        return _semester_start(today)
    return None  # all-time


def _minutes_annotation(start):
    """Coalesced sum of study minutes, optionally restricted to a date window."""
    if start is None:
        return Coalesce(Sum("study_sessions__minutes"), 0)
    return Coalesce(
        Sum(
            "study_sessions__minutes",
            filter=Q(study_sessions__completed_at__date__gte=start),
        ),
        0,
    )


def leaderboard(request):
    my_group = request.user.academic_group if request.user.is_authenticated else ""
    return render(
        request,
        "productivity/leaderboard.html",
        {"groups": AcademicGroup.choices, "my_group": my_group},
    )


class LeaderboardAPIView(APIView):
    """Ranks users by focus minutes in a time window, filtered by academic group."""

    def get(self, request):
        window = request.query_params.get("window", "all")
        if window not in WINDOWS:
            window = "all"
        group = request.query_params.get("group", "global")
        sort = request.query_params.get("sort", "minutes")

        start = _window_start(window, timezone.localdate())
        minutes_field = _minutes_annotation(start)

        users = User.objects.filter(is_active=True).select_related("stats")
        if group != "global":
            users = users.filter(academic_group=group)
        users = users.annotate(minutes=minutes_field).filter(minutes__gt=0)
        if sort == "streak":
            users = users.order_by("-stats__current_streak", "-minutes")
        else:
            users = users.order_by("-minutes", "-stats__current_streak")

        me_pk = request.user.pk if request.user.is_authenticated else None
        reveal = request.user.is_authenticated and request.user.is_superuser
        rows = []
        for index, user in enumerate(users[:50], start=1):
            is_me = user.pk == me_pk
            rows.append(
                {
                    "rank": index,
                    "name": "You" if is_me else user.board_name(reveal=reveal),
                    "group": user.get_academic_group_display() if user.academic_group else "",
                    "minutes": user.minutes,
                    "streak": user.stats.current_streak if user.stats else 0,
                    "is_me": is_me,
                }
            )

        me = self._my_position(request.user, group, start) if me_pk else None
        return Response(
            {"window": window, "group": group, "sort": sort, "rows": rows, "me": me}
        )

    def _my_position(self, user, group, start):
        sessions = StudySession.objects.filter(user=user)
        if start is not None:
            sessions = sessions.filter(completed_at__date__gte=start)
        my_minutes = sessions.aggregate(total=Sum("minutes"))["total"] or 0

        peers = User.objects.filter(is_active=True)
        if group != "global":
            peers = peers.filter(academic_group=group)
        ahead = (
            peers.annotate(minutes=_minutes_annotation(start))
            .filter(minutes__gt=my_minutes)
            .count()
        )
        return {
            "rank": ahead + 1,
            "minutes": my_minutes,
            "streak": user.stats.current_streak,
        }
