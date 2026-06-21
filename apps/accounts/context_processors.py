from .models import ThemePreference


def user_theme(request):
    """Expose a signed-in user's explicit theme so it overrides localStorage.

    Empty string when the user is anonymous or prefers the system theme — in
    those cases the client falls back to localStorage / prefers-color-scheme.
    """
    user = getattr(request, "user", None)
    if user and user.is_authenticated and user.theme_preference != ThemePreference.SYSTEM:
        return {"user_theme": user.theme_preference}
    return {"user_theme": ""}
