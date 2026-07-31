from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("forgot/", views.forgot_password, name="forgot_password"),
    path("password/", views.ChangePasswordView.as_view(), name="change_password"),
    path("theme/", views.update_theme, name="update_theme"),
]
