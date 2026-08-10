"""Project-level middleware."""

import datetime
import hashlib
import time

from django.core.cache import cache
from django.http import HttpResponsePermanentRedirect
from django.utils import timezone

# Presence tracking: which clients were seen in the last WINDOW seconds.
# A single cache entry holds {client_id: (last_seen, username_or_None)} so the
# owner dashboard can show "who's online" without a DB write per request.
# Approximate by design: a sliding window, and the locmem cache is per-process
# (exact on a single-worker host like the PA free tier, a bit off otherwise).
PRESENCE_KEY = "presence:online"
PRESENCE_WINDOW = 300  # 5 minutes

# Traffic analytics: one live cache bucket per day
# ({"views": int, "sessions": {client_id: (first_seen, last_seen)}}), flushed
# into DailyStats by the end-of-day rollover. No DB write per request.
STATS_DAY_PREFIX = "stats:day:"
STATS_DAYS_KEY = "stats:days"      # day keys that still have a live bucket
STATS_CURRENT_KEY = "stats:current"  # today's day key
STATS_BUCKET_TTL = 172800          # keep live buckets 48h so rollover finds them
SESSION_TIME_CAP = 7200            # cap one visitor-day at 2h (idle distortion)

_SKIP_PREFIXES = ("/static/", "/media/", "/healthz")


def _client_identity(request):
    """(client_id, username_or_None) — session key for members, IP hash for guests."""
    user = request.user
    if user.is_authenticated:
        return "s:" + (request.session.session_key or user.username), user.username
    ip = (
        request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR", "unknown")
    )
    return "g:" + hashlib.sha1(ip.encode()).hexdigest()[:16], None


class PermissionsPolicyMiddleware:
    """Send a restrictive Permissions-Policy header on every response, switching
    off browser features the site never uses (defence-in-depth)."""

    POLICY = "geolocation=(), camera=(), microphone=(), payment=(), usb=()"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Permissions-Policy"] = self.POLICY
        return response


class PresenceMiddleware:
    """Record each visitor's last-seen time in the cache (owner dashboard).

    Members are keyed by session key and stored with their username; guests by
    a hash of their IP. Runs after AuthenticationMiddleware so request.user is
    available. Fail-open: a broken cache must never break the site.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(_SKIP_PREFIXES):
            self._touch(request)
        return self.get_response(request)

    def _touch(self, request):
        try:
            client_id, label = _client_identity(request)
            now = time.time()
            online = cache.get(PRESENCE_KEY) or {}
            online = {
                cid: seen for cid, seen in online.items() if now - seen[0] < PRESENCE_WINDOW
            }
            online[client_id] = (now, label)
            cache.set(PRESENCE_KEY, online, timeout=PRESENCE_WINDOW * 2)
        except Exception:
            pass


def get_online_summary():
    """Who's on the site right now: member usernames + a guest count."""
    online = cache.get(PRESENCE_KEY) or {}
    now = time.time()
    members = sorted(
        label for _, (seen, label) in online.items() if label and now - seen < PRESENCE_WINDOW
    )
    guests = sum(
        1 for _, (seen, label) in online.items() if not label and now - seen < PRESENCE_WINDOW
    )
    return {"members": members, "guests": guests}


class AnalyticsMiddleware:
    """Count daily visitors / page views / time-on-site in a cache bucket.

    Per request this only touches the cache; finished days are rolled into
    ``DailyStats`` (see ``flush_stats_day``). Fail-open like the presence
    middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(_SKIP_PREFIXES):
            self._track(request)
        return self.get_response(request)

    def _track(self, request):
        try:
            today = timezone.localdate().isoformat()
            key = STATS_DAY_PREFIX + today
            now = time.time()
            client_id, _ = _client_identity(request)

            bucket = cache.get(key) or {"views": 0, "sessions": {}}
            bucket["views"] += 1
            first, _last = bucket["sessions"].get(client_id, (now, now))
            bucket["sessions"][client_id] = (first, now)
            cache.set(key, bucket, timeout=STATS_BUCKET_TTL)

            days = cache.get(STATS_DAYS_KEY) or []
            if key not in days:
                days.append(key)
                cache.set(STATS_DAYS_KEY, days, timeout=None)

            if cache.get(STATS_CURRENT_KEY) != key:
                self._rollover(except_key=key)
                cache.set(STATS_CURRENT_KEY, key, timeout=None)
        except Exception:
            pass

    def _rollover(self, except_key):
        """The day changed: flush every older live bucket into the database."""
        days = cache.get(STATS_DAYS_KEY) or []
        remaining = []
        for day_key in days:
            if day_key == except_key:
                remaining.append(day_key)
                continue
            flush_stats_day(day_key)
            cache.delete(day_key)
        cache.set(STATS_DAYS_KEY, remaining, timeout=None)


def _bucket_totals(bucket):
    """(visitors, page_views, capped total seconds) for a live bucket."""
    sessions = bucket["sessions"].values()
    total = sum(
        min(max(int(last - first), 0), SESSION_TIME_CAP) for first, last in sessions
    )
    return len(bucket["sessions"]), bucket["views"], total


def get_today_stats():
    """Today's live (not yet flushed) traffic numbers."""
    key = STATS_DAY_PREFIX + timezone.localdate().isoformat()
    bucket = cache.get(key) or {"views": 0, "sessions": {}}
    visitors, views, total = _bucket_totals(bucket)
    return {"visitors": visitors, "page_views": views, "total_time_seconds": total}


def flush_stats_day(day_key):
    """Persist a live day bucket into DailyStats. Returns the row (or None)."""
    from apps.administration.models import DailyStats  # late import: app registry

    bucket = cache.get(day_key)
    if not bucket:
        return None
    day = datetime.date.fromisoformat(day_key[len(STATS_DAY_PREFIX):])
    visitors, views, total = _bucket_totals(bucket)
    row, _ = DailyStats.objects.update_or_create(
        date=day,
        defaults={
            "visitors": visitors,
            "page_views": views,
            "total_time_seconds": total,
        },
    )
    return row


class DomainRedirectMiddleware:
    """301-redirect the old Render domain to the canonical one.

    Google indexed nhsm-website.onrender.com first; a permanent redirect
    moves that ranking to nhsmhub.com instead of splitting it across two
    domains serving identical content. Registered first in MIDDLEWARE so
    old-domain requests bounce before doing any work.
    """

    OLD_HOST = "nhsm-website.onrender.com"
    CANONICAL = "https://nhsmhub.com"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.get_host() == self.OLD_HOST:
            return HttpResponsePermanentRedirect(
                self.CANONICAL + request.get_full_path()
            )
        return self.get_response(request)
