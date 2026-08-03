from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from config.throttle import rate_limit

from .forms import (
    ProfileForm,
    RecoveryForm,
    RegistrationForm,
    StyledPasswordChangeForm,
)
from .models import ThemePreference, generate_recovery_code


@rate_limit("register", limit=10, period=3600)
def register(request):
    if request.user.is_authenticated:
        return redirect("profile")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Explicit backend: django-axes adds a second auth backend, so login()
            # can no longer guess which one to attach to the session.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(
                request,
                f"Welcome to NHSM Hub! Your recovery code is {user.recovery_code} — "
                "save it somewhere safe. It's the only way to reset your password "
                "if you forget it (it's also on your profile).",
            )
            return redirect("profile")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@rate_limit("forgot", limit=10, period=3600, identity="username")
def forgot_password(request):
    """Self-service reset: username + personal recovery code → new password.

    A successful reset burns the old code (a fresh one is issued) and logs the
    user straight in — they just proved ownership of the account.
    """
    if request.user.is_authenticated:
        return redirect("profile")
    if request.method == "POST":
        form = RecoveryForm(request.POST)
        if form.is_valid():
            user = form.user
            user.set_password(form.cleaned_data["new_password1"])
            user.recovery_code = generate_recovery_code()
            user.save(update_fields=["password", "recovery_code"])
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(
                request,
                "Password reset — welcome back! Your new recovery code is "
                f"{user.recovery_code} (the old one no longer works).",
            )
            return redirect("profile")
    else:
        form = RecoveryForm()
    return render(request, "accounts/forgot_password.html", {"form": form})


class ChangePasswordView(PasswordChangeView):
    """Logged-in password change from the profile page."""

    template_name = "accounts/change_password.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        messages.success(self.request, "Password changed.")
        return super().form_valid(form)


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(
        request, "accounts/profile.html", {"form": form, "stats": request.user.stats}
    )


@require_POST
@login_required
def update_theme(request):
    """Persist a signed-in user's theme choice (called by the nav toggle)."""
    theme = request.POST.get("theme")
    if theme in ThemePreference.values:
        request.user.theme_preference = theme
        request.user.save(update_fields=["theme_preference"])
        return JsonResponse({"ok": True, "theme": theme})
    return JsonResponse({"ok": False}, status=400)
