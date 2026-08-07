from django.contrib.auth.decorators import user_passes_test


def _is_admin(user):
    return user.is_authenticated and user.is_admin


def _is_owner(user):
    return user.is_authenticated and user.is_owner


# Redirects anonymous and non-admin users to the login page.
admin_required = user_passes_test(_is_admin)

# The owner (superuser) only — a tier above the admin panel.
owner_required = user_passes_test(_is_owner)
