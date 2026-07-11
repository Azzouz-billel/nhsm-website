"""Settings shared by every environment.

Environment-specific modules (``development``, ``production``) import everything
from here and override what differs. Secrets come from the environment / a local
``.env`` file via django-environ; sensible dev defaults keep the app runnable
without one.
"""

import sys
from pathlib import Path

import environ

# config/settings/base.py -> project root is three levels up.
BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
)
# Read .env if present. The file is optional and never required for dev.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Donation links (paste your Chargily / RedotPay payment-page URLs). An env var
# of the same name overrides these defaults if set.
CHARGILY_DONATION_URL = env(
    "CHARGILY_DONATION_URL",
    default="http://pay.chargily.com/payment-links/01kwyrqtjam3xmf3p1s0wpzshm",
)
REDOTPAY_DONATION_URL = env("REDOTPAY_DONATION_URL", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # Third-party
    "rest_framework",
    "axes",
    # Local
    "apps.accounts",
    "apps.resources",
    "apps.moderation",
    "apps.productivity",
    "apps.requests",
    "apps.administration",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.PermissionsPolicyMiddleware",
    "axes.middleware.AxesMiddleware",  # must be last
]

# --- Security: brute-force lockout (django-axes) + headers --------------------
# Disable axes under the test runner so unrelated auth tests aren't affected; the
# lockout test re-enables it explicitly with override_settings.
TESTING = "test" in sys.argv
AXES_ENABLED = not TESTING
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours locked out after too many failures
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_RESET_ON_SUCCESS = True
AXES_HTTP_RESPONSE_CODE = 429

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # must come first
    "django.contrib.auth.backends.ModelBackend",
]
if TESTING:
    # A single backend keeps Client.force_login() usable across the suite without
    # a backend hint; the lockout test re-adds axes explicitly via override_settings.
    AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.user_theme",
                "apps.administration.context_processors.site_bulletins",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Custom user model — must be set before the first migration (see plan).
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "profile"
LOGOUT_REDIRECT_URL = "home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Algiers"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Production swaps staticfiles for WhiteNoise's compressed-manifest storage
# (which needs `collectstatic`); dev and tests use the plain storage.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
}
