from django import template

register = template.Library()


@register.filter
def stars(value):
    """Render a 0–5 score as filled/empty stars, e.g. 4 → ★★★★☆."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = 0
    n = max(0, min(5, n))
    return "★" * n + "☆" * (5 - n)
