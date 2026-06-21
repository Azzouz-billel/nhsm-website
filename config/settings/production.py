"""Production settings: Postgres, optional S3 media, hardened security.

Everything sensitive is read from the environment. Deploy with at least
SECRET_KEY, DATABASE_URL and ALLOWED_HOSTS set.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["nhsmhub.online"])

# Hashed, compressed static files served by WhiteNoise (run collectstatic).
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
}

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# Optional S3 media storage — enabled only when a bucket is configured.
if env("AWS_STORAGE_BUCKET_NAME", default=""):
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}  # noqa: F405
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="eu-west-1")
    AWS_QUERYSTRING_AUTH = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
