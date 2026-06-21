from django.contrib import admin

from .models import StudySession


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "minutes", "completed_at")
    list_filter = ("completed_at", "subject__semester")
    search_fields = ("user__username", "subject__name")
