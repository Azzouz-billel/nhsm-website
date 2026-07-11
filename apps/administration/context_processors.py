import hashlib

from .models import Bulletin


def site_bulletins(request):
    """Expose active news bulletins + a content signature to every template.

    The signature changes whenever the news changes, so a user who hid the bar
    sees it again once there's something new. Guarded so a page can't 500
    before the table exists (e.g. a fresh deploy between collectstatic and
    migrate)."""
    try:
        items = list(Bulletin.objects.filter(is_active=True))
    except Exception:
        return {"site_bulletins": [], "news_signature": ""}

    raw = "|".join(f"{b.pk}:{b.text_en}:{b.text_ar}:{b.link}" for b in items)
    signature = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12] if items else ""
    return {"site_bulletins": items, "news_signature": signature}
