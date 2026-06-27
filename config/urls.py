from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def google_site_verification(request):
    """Serve the Google Search Console ownership token at the site root."""
    return HttpResponse(
        "google-site-verification: googleb55567535a46ef21.html",
        content_type="text/html",
    )


def health_check(request):
    """Lightweight liveness endpoint with no DB access. An external uptime
    pinger hits this to keep the free Render instance awake without waking the
    (scale-to-zero) database."""
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("googleb55567535a46ef21.html", google_site_verification),
    path("healthz", health_check),
    path("admin/", admin.site.urls),
    path("api/", include("apps.resources.api_urls")),
    path("api/", include("apps.productivity.api_urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("moderation/", include("apps.moderation.urls")),
    path("manage/", include("apps.administration.urls")),
    path("requests/", include("apps.requests.urls")),
    path("", include("apps.productivity.urls")),
    path("", include("apps.resources.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
