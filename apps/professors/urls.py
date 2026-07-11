from django.urls import path

from . import views

urlpatterns = [
    path("", views.professor_list, name="professor_list"),
    path("<int:pk>/", views.professor_detail, name="professor_detail"),
    path("<int:pk>/rate/", views.rate, name="professor_rate"),
    path("ratings/<int:pk>/hide/", views.rating_hide, name="professor_rating_hide"),
    path("ratings/<int:pk>/delete/", views.rating_delete, name="professor_rating_delete"),
]
