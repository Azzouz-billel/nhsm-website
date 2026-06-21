"""Deploy settings for PythonAnywhere (free tier · SQLite · PA static server).

On the server, create a file named ``.env`` next to ``manage.py`` containing:

    SECRET_KEY=<a long random string>
    ALLOWED_HOSTS=<your-username>.pythonanywhere.com
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, MIDDLEWARE, STORAGES, env

DEBUG = False

# Read from the .env file (so you never edit code to change your domain).
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
# Django 4+ needs this or login/upload POSTs fail CSRF (403):
CSRF_TRUSTED_ORIGINS = ["https://" + host for host in ALLOWED_HOSTS]

# Real secret key from the .env (never committed to git).
SECRET_KEY = env("SECRET_KEY")

# SQLite — the db.sqlite3 in the project root.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Static & media served by PythonAnywhere's own static server (not WhiteNoise).
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Plain storage → no hashed manifest → avoids the classic
# "Missing staticfiles manifest entry" 500 error.
STORAGES["staticfiles"] = {
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}

# Drop WhiteNoise — PythonAnywhere serves /static/ for you.
if "whitenoise.middleware.WhiteNoiseMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("whitenoise.middleware.WhiteNoiseMiddleware")

# Cookie security over HTTPS (PythonAnywhere serves your site on https).
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Keep the forced-HTTPS redirect OFF on the free tier (avoids redirect loops).
SECURE_SSL_REDIRECT = False
