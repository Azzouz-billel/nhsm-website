from django.urls import path

from . import views

urlpatterns = [
    path("", views.queue, name="moderation_queue"),
    path("<int:pk>/review/", views.review, name="moderation_review"),
]
