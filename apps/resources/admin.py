from django.contrib import admin

from .models import ExamPaper, Resource, Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "semester", "speciality")
    list_filter = ("semester", "speciality")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "resource_type", "status", "created_at")
    list_filter = ("status", "resource_type", "subject__semester", "subject__speciality")
    search_fields = ("title", "description")
    autocomplete_fields = ("subject",)
    actions = ("approve_selected", "reject_selected")

    @admin.action(description="Approve selected resources")
    def approve_selected(self, request, queryset):
        for resource in queryset:
            resource.approve(by_user=request.user)
        self.message_user(request, f"Approved {queryset.count()} resource(s).")

    @admin.action(description="Reject selected resources")
    def reject_selected(self, request, queryset):
        for resource in queryset:
            resource.reject(by_user=request.user)
        self.message_user(request, f"Rejected {queryset.count()} resource(s).")


@admin.register(ExamPaper)
class ExamPaperAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "year", "exam_type", "has_solution")
    list_filter = ("year", "exam_type", "has_solution", "subject__semester", "subject__speciality")
    search_fields = ("title", "subject__name")
    autocomplete_fields = ("subject",)
