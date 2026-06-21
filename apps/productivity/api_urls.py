from django.urls import path

from . import views

urlpatterns = [
    path(
        "study-sessions",
        views.StudySessionCreateAPIView.as_view(),
        name="api_study_session_create",
    ),
    path("leaderboard", views.LeaderboardAPIView.as_view(), name="api_leaderboard"),
]
