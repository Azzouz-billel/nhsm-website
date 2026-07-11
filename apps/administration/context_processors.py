from .models import Bulletin


def site_bulletins(request):
    """Expose the active news bulletins to every template (footer ticker).

    Guarded so a page can't 500 before the table exists (e.g. a fresh deploy
    between collectstatic and migrate)."""
    try:
        return {"site_bulletins": list(Bulletin.objects.filter(is_active=True))}
    except Exception:
        return {"site_bulletins": []}
