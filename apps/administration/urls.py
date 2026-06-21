from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="manage_dashboard"),

    path("resources/", views.resource_list, name="manage_resources"),
    path("resources/new/", views.resource_form, name="manage_resource_create"),
    path("resources/<int:pk>/", views.resource_form, name="manage_resource_edit"),
    path("resources/<int:pk>/delete/", views.resource_delete, name="manage_resource_delete"),

    path("subjects/", views.subject_list, name="manage_subjects"),
    path("subjects/new/", views.subject_form, name="manage_subject_create"),
    path("subjects/<int:pk>/", views.subject_form, name="manage_subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="manage_subject_delete"),

    path("exams/", views.exam_list, name="manage_exams"),
    path("exams/new/", views.exam_form, name="manage_exam_create"),
    path("exams/<int:pk>/", views.exam_form, name="manage_exam_edit"),
    path("exams/<int:pk>/delete/", views.exam_delete, name="manage_exam_delete"),

    path("users/", views.user_list, name="manage_users"),
    path("users/<int:pk>/", views.user_form, name="manage_user_edit"),
]
