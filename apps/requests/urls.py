from django.urls import path

from . import views

urlpatterns = [
    path("", views.board, name="request_board"),
    path("<int:pk>/vote/", views.vote, name="request_vote"),
    path("<int:pk>/status/", views.update_status, name="request_status"),
]
