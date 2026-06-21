from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ProfileForm, RegistrationForm
from .models import ThemePreference


def register(request):
    if request.user.is_authenticated:
        return redirect("profile")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to NHSM Hub! Your account is ready.")
            return redirect("profile")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
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
