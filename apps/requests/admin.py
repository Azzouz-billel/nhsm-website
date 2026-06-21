from django.contrib import admin

from .models import RequestVote, ResourceRequest


@admin.register(ResourceRequest)
class ResourceRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "status", "author", "created_at")
    list_filter = ("status", "subject__semester")
    search_fields = ("title", "description")


@admin.register(RequestVote)
class RequestVoteAdmin(admin.ModelAdmin):
    list_display = ("user", "request", "created_at")
    search_fields = ("user__username", "request__title")
