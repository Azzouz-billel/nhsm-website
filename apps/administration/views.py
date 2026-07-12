from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Role, User
from apps.requests.models import ResourceRequest
from apps.resources.models import ExamPaper, Resource, ResourceStatus, Subject

from apps.professors.models import Professor, ProfessorRating

from .decorators import admin_required
from .forms import (
    BulletinAdminForm,
    ExamAdminForm,
    ProfessorAdminForm,
    ResourceAdminForm,
    SubjectAdminForm,
    UserRoleForm,
)
from .models import Bulletin


@admin_required
def dashboard(request):
    context = {
        "resource_total": Resource.objects.count(),
        "resource_pending": Resource.objects.filter(
            status=ResourceStatus.PENDING
        ).count(),
        "exam_total": ExamPaper.objects.count(),
        "subject_total": Subject.objects.count(),
        "request_total": ResourceRequest.objects.count(),
        "user_total": User.objects.count(),
        "admin_total": User.objects.filter(role=Role.ADMIN).count(),
        "pending_reviews": ProfessorRating.objects.filter(is_approved=False).count(),
    }
    return render(request, "manage/dashboard.html", context)


# ----------------------------------------------------------------- resources
@admin_required
def resource_list(request):
    resources = Resource.objects.select_related("subject")
    status = request.GET.get("status")
    if status in ResourceStatus.values:
        resources = resources.filter(status=status)
    return render(
        request,
        "manage/resources.html",
        {
            "resources": resources,
            "statuses": ResourceStatus.choices,
            "active_status": status or "",
        },
    )


@admin_required
def resource_form(request, pk=None):
    instance = get_object_or_404(Resource, pk=pk) if pk else None
    if request.method == "POST":
        form = ResourceAdminForm(request.POST, instance=instance)
        if form.is_valid():
            resource = form.save(commit=False)
            if resource.uploader_id is None:
                resource.uploader = request.user
            resource.save()
            messages.success(request, "Resource saved.")
            return redirect("manage_resources")
    else:
        initial = None if instance else {"status": ResourceStatus.APPROVED}
        form = ResourceAdminForm(instance=instance, initial=initial)
    return render(
        request,
        "manage/form.html",
        {
            "form": form,
            "heading": "Edit resource" if instance else "Add resource",
            "back_url": "manage_resources",
        },
    )


@require_POST
@admin_required
def resource_delete(request, pk):
    get_object_or_404(Resource, pk=pk).delete()
    messages.success(request, "Resource deleted.")
    return redirect("manage_resources")


# ------------------------------------------------------------------ subjects
@admin_required
def subject_list(request):
    return render(
        request,
        "manage/subjects.html",
        {"subjects": Subject.objects.all()},
    )


@admin_required
def subject_form(request, pk=None):
    instance = get_object_or_404(Subject, pk=pk) if pk else None
    if request.method == "POST":
        form = SubjectAdminForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Subject saved.")
            return redirect("manage_subjects")
    else:
        form = SubjectAdminForm(instance=instance)
    return render(
        request,
        "manage/form.html",
        {
            "form": form,
            "heading": "Edit subject" if instance else "Add subject",
            "back_url": "manage_subjects",
        },
    )


@require_POST
@admin_required
def subject_delete(request, pk):
    get_object_or_404(Subject, pk=pk).delete()
    messages.success(request, "Subject deleted.")
    return redirect("manage_subjects")


# --------------------------------------------------------------------- exams
@admin_required
def exam_list(request):
    return render(
        request,
        "manage/exams.html",
        {"exams": ExamPaper.objects.select_related("subject")},
    )


@admin_required
def exam_form(request, pk=None):
    instance = get_object_or_404(ExamPaper, pk=pk) if pk else None
    if request.method == "POST":
        form = ExamAdminForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Exam paper saved.")
            return redirect("manage_exams")
    else:
        form = ExamAdminForm(instance=instance)
    return render(
        request,
        "manage/form.html",
        {
            "form": form,
            "heading": "Edit exam paper" if instance else "Add exam paper",
            "back_url": "manage_exams",
        },
    )


@require_POST
@admin_required
def exam_delete(request, pk):
    get_object_or_404(ExamPaper, pk=pk).delete()
    messages.success(request, "Exam paper deleted.")
    return redirect("manage_exams")


# --------------------------------------------------------------------- users
@admin_required
def user_list(request):
    return render(
        request,
        "manage/users.html",
        {"users": User.objects.order_by("-date_joined")},
    )


@admin_required
def user_form(request, pk):
    instance = get_object_or_404(User, pk=pk)
    # Only the owner may edit an admin or the owner; admins manage students/approvers.
    if instance.is_admin and not request.user.is_superuser:
        return HttpResponseForbidden("Only the owner can edit an admin.")
    if request.method == "POST":
        form = UserRoleForm(request.POST, instance=instance, editor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {instance.username}.")
            return redirect("manage_users")
    else:
        form = UserRoleForm(instance=instance, editor=request.user)
    return render(
        request,
        "manage/form.html",
        {"form": form, "heading": f"Edit {instance.username}", "back_url": "manage_users"},
    )


# ----------------------------------------------------------------- bulletins
@admin_required
def bulletin_list(request):
    return render(
        request,
        "manage/bulletins.html",
        {"bulletins": Bulletin.objects.all()},
    )


@admin_required
def bulletin_form(request, pk=None):
    instance = get_object_or_404(Bulletin, pk=pk) if pk else None
    if request.method == "POST":
        form = BulletinAdminForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Bulletin saved.")
            return redirect("manage_bulletins")
    else:
        form = BulletinAdminForm(instance=instance)
    return render(
        request,
        "manage/form.html",
        {
            "form": form,
            "heading": "Edit bulletin" if instance else "Add bulletin",
            "back_url": "manage_bulletins",
        },
    )


@require_POST
@admin_required
def bulletin_delete(request, pk):
    get_object_or_404(Bulletin, pk=pk).delete()
    messages.success(request, "Bulletin deleted.")
    return redirect("manage_bulletins")


# ---------------------------------------------------------------- professors
@admin_required
def professor_list(request):
    return render(
        request,
        "manage/professors.html",
        {"professors": Professor.objects.all()},
    )


@admin_required
def professor_form(request, pk=None):
    instance = get_object_or_404(Professor, pk=pk) if pk else None
    if request.method == "POST":
        form = ProfessorAdminForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Professor saved.")
            return redirect("manage_professors")
    else:
        form = ProfessorAdminForm(instance=instance)
    return render(
        request,
        "manage/form.html",
        {
            "form": form,
            "heading": "Edit professor" if instance else "Add professor",
            "back_url": "manage_professors",
        },
    )


@require_POST
@admin_required
def professor_delete(request, pk):
    get_object_or_404(Professor, pk=pk).delete()
    messages.success(request, "Professor deleted.")
    return redirect("manage_professors")


@admin_required
def review_queue(request):
    """Pending professor ratings awaiting an admin's approval (pre-moderation)."""
    pending = ProfessorRating.objects.filter(is_approved=False).select_related(
        "professor", "user"
    )
    return render(request, "manage/reviews.html", {"pending": pending})
