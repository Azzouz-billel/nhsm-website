from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserStats


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "academic_group", "is_staff")
    list_filter = ("role", "academic_group", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (
        (
            "NHSM profile",
            {
                "fields": (
                    "role",
                    "academic_group",
                    "display_name",
                    "is_anonymous_on_board",
                    "theme_preference",
                )
            },
        ),
    )


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "total_study_minutes",
        "total_sessions",
        "current_streak",
        "contributions",
    )
    search_fields = ("user__username",)
