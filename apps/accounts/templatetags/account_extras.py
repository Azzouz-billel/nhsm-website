from django import template

register = template.Library()


@register.filter
def reveal_name(user, viewer):
    """Board name for `user`, revealing the real name to the owner (superuser)."""
    reveal = getattr(viewer, "is_authenticated", False) and getattr(
        viewer, "is_superuser", False
    )
    return user.board_name(reveal=reveal)
