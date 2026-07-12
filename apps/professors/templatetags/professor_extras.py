from django import template

from ..models import TAG_LABELS

register = template.Library()


@register.filter
def tag_label(key):
    """Map a rating-tag key to its human label (e.g. 'clear' → 'Clear explanations')."""
    return TAG_LABELS.get(key, key)


@register.filter
def stars(value):
    """Render a 0–5 score as filled/empty stars, e.g. 4 → ★★★★☆."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = 0
    n = max(0, min(5, n))
    return "★" * n + "☆" * (5 - n)
