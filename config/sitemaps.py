"""Sitemap for the public, crawlable pages."""

from django.contrib import sitemaps
from django.urls import reverse


class StaticViewSitemap(sitemaps.Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return [
            "home",
            "resource_library",
            "annales",
            "timer",
            "leaderboard",
            "request_board",
            "contact",
            "register",
            "login",
        ]

    def location(self, item):
        return reverse(item)
