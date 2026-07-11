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

    path("bulletins/", views.bulletin_list, name="manage_bulletins"),
    path("bulletins/new/", views.bulletin_form, name="manage_bulletin_create"),
    path("bulletins/<int:pk>/", views.bulletin_form, name="manage_bulletin_edit"),
    path("bulletins/<int:pk>/delete/", views.bulletin_delete, name="manage_bulletin_delete"),

    path("professors/", views.professor_list, name="manage_professors"),
    path("professors/new/", views.professor_form, name="manage_professor_create"),
    path("professors/<int:pk>/", views.professor_form, name="manage_professor_edit"),
    path("professors/<int:pk>/delete/", views.professor_delete, name="manage_professor_delete"),

    path("reviews/", views.review_queue, name="manage_reviews"),
]
