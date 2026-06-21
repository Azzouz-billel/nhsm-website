from django.urls import path

from . import views

urlpatterns = [
    path("resources/search", views.ResourceSearchAPIView.as_view(), name="api_resource_search"),
    path("exams/search", views.ExamSearchAPIView.as_view(), name="api_exam_search"),
]
