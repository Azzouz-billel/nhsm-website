from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from config.sitemaps import StaticViewSitemap

SITEMAPS = {"static": StaticViewSitemap}


def robots_txt(request):
    """Tell crawlers what to index and where the sitemap is."""
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /manage/",
        "Disallow: /accounts/",
        "Allow: /",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


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
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.resources.api_urls")),
    path("api/", include("apps.productivity.api_urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("moderation/", include("apps.moderation.urls")),
    path("manage/", include("apps.administration.urls")),
    path("requests/", include("apps.requests.urls")),
    path("professors/", include("apps.professors.urls")),
    path("", include("apps.productivity.urls")),
    path("", include("apps.resources.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
