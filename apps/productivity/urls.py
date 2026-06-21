from django.urls import path

from . import views

urlpatterns = [
    path("timer/", views.timer, name="timer"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
]
