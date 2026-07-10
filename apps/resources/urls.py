from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("resources/", views.resource_library, name="resource_library"),
    path("resources/upload/", views.upload_resource, name="resource_upload"),
    path("annales/", views.annales, name="annales"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]
