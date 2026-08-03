"""Tiny cache-backed rate limiter for sensitive form POSTs.

django-axes already guards the login page, but nothing stops unlimited attempts
on the other write endpoints (account recovery, registration, voting, rating).
This decorator closes that gap with Django's cache framework — no extra deps.

The limiter is a safety net, not a core feature: it is disabled under the test
runner (like axes) and fails open if the cache backend is down, so it can never
take the site offline.
"""

import hashlib
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


def _client_ip(request):
    """Best-effort client IP. Behind a proxy (Render / PythonAnywhere) the
    platform sets X-Forwarded-For; a determined attacker can spoof it, so treat
    this as a deterrent — pair it with per-identity keys where one exists."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def rate_limit(scope, limit, period, identity=None):
    """Allow ``limit`` POSTs per ``period`` seconds per client for ``scope``.

    ``identity`` (optional) names a POST field (e.g. "username") whose value is
    mixed into the throttle key, so guessing against many accounts from
    rotating IPs still hits a per-account wall.

    Over the limit the client gets a plain 429.
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method == "POST" and getattr(
                settings, "RATELIMIT_ENABLED", True
            ):
                parts = [scope, _client_ip(request) or "unknown"]
                if identity:
                    parts.append(request.POST.get(identity, ""))
                digest = hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]
                key = f"rl:{scope}:{digest}"
                try:
                    count = cache.get(key, 0)
                    if count >= limit:
                        return HttpResponse(
                            "Too many attempts — please try again later.",
                            status=429,
                            content_type="text/plain",
                        )
                    cache.set(key, count + 1, timeout=period)
                except Exception:
                    pass  # cache trouble must never block real users
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
