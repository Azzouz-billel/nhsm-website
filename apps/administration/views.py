from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import Role, User, generate_recovery_code
from apps.productivity.models import StudySession
from apps.requests.models import RequestStatus, RequestVote, ResourceRequest
from apps.resources.models import ExamPaper, Resource, ResourceStatus, Subject

from apps.professors.models import Professor, ProfessorRating
from apps.moderation.models import GuestbookComment

from config.middleware import get_online_summary, get_today_stats

from .decorators import admin_required, owner_required
from .forms import (
    BulletinAdminForm,
    ExamAdminForm,
    ProfessorAdminForm,
    ResourceAdminForm,
    SubjectAdminForm,
    UserRoleForm,
)
from .models import Bulletin, DailyStats


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


@require_POST
@admin_required
def user_regenerate_code(request, pk):
    """Issue a fresh recovery code for a student who lost both password and code.

    The new code is shown to the admin (once, via the flash message) so they can
    pass it to the student; the old code stops working immediately.
    """
    instance = get_object_or_404(User, pk=pk)
    # Only the owner may touch an admin/owner account (same rule as user_form).
    if instance.is_admin and not request.user.is_superuser:
        return HttpResponseForbidden("Only the owner can reset an admin's code.")
    instance.recovery_code = generate_recovery_code()
    instance.save(update_fields=["recovery_code"])
    messages.success(
        request,
        f"New recovery code for {instance.username}: {instance.recovery_code} "
        "— pass it to them; the old code no longer works.",
    )
    return redirect("manage_users")


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


@admin_required
def comment_list(request):
    """All wall-of-love comments: pending ones first so nothing waits unseen."""
    comments = GuestbookComment.objects.select_related("author").order_by(
        "is_approved", "-is_pinned", "-created_at"
    )
    return render(request, "manage/comments.html", {"comments": comments})


@require_POST
@admin_required
def comment_review(request, pk):
    comment = get_object_or_404(GuestbookComment, pk=pk)
    action = request.POST.get("action")
    if action == "approve":
        comment.is_approved = True
        comment.save(update_fields=["is_approved"])
        messages.success(request, "Comment published on the home page.")
    elif action == "hide":
        comment.is_approved = False
        comment.save(update_fields=["is_approved"])
        messages.success(request, "Comment hidden from the home page.")
    elif action == "pin":
        comment.is_pinned = True
        comment.is_approved = True
        comment.save(update_fields=["is_pinned", "is_approved"])
        messages.success(request, "Comment pinned to top of Wall of Love.")
    elif action == "unpin":
        comment.is_pinned = False
        comment.save(update_fields=["is_pinned"])
        messages.success(request, "Comment unpinned.")
    elif action == "delete":
        comment.delete()
        messages.success(request, "Comment deleted.")
    return redirect("manage_comments")


# --------------------------------------------------------------------- owner
@owner_required
def owner_dashboard(request):
    """Owner-only page: who's on the site right now + total site-wide info."""
    today = timezone.localdate()
    week_ago = today - timedelta(days=7)
    online = get_online_summary()

    study = StudySession.objects.aggregate(
        sessions=Count("id"), minutes=Coalesce(Sum("minutes"), 0)
    )
    today_minutes = StudySession.objects.filter(
        completed_at__date=today
    ).aggregate(total=Coalesce(Sum("minutes"), 0))["total"]

    # Traffic: live numbers for today, flushed rows for the days before.
    def _avg(seconds, visitors):
        if not visitors:
            return "—"
        per = seconds // visitors
        return f"{per // 60}m {per % 60:02d}s"

    live = get_today_stats()
    traffic_today = {
        "date": today,
        "visitors": live["visitors"],
        "page_views": live["page_views"],
        "avg": _avg(live["total_time_seconds"], live["visitors"]),
    }
    traffic_days = list(DailyStats.objects.all()[:7])
    for row in traffic_days:
        row.avg = _avg(row.total_time_seconds, row.visitors)

    # Most opened modules: opens summed per subject — overall top 5 + top 3
    # per semester.
    module_rows = (
        Resource.objects.filter(opens__gt=0)
        .values("subject__name", "subject__semester")
        .annotate(total=Sum("opens"))
        .order_by("-total")
    )

    def _module(row):
        return {
            "name": row["subject__name"],
            "semester": row["subject__semester"],
            "total": row["total"],
        }

    top_modules = [_module(r) for r in module_rows[:5]]
    by_semester = {}
    for row in module_rows:
        bucket = by_semester.setdefault(row["subject__semester"], [])
        if len(bucket) < 3:
            bucket.append(_module(row))
    modules_by_semester = sorted(by_semester.items())

    comment_pending = GuestbookComment.objects.filter(is_approved=False).count()

    context = {
        "online_members": online["members"],
        "online_guests": online["guests"],
        "online_total": len(online["members"]) + online["guests"],
        # Users
        "user_total": User.objects.count(),
        "student_total": User.objects.filter(role=Role.STUDENT).count(),
        "approver_total": User.objects.filter(role=Role.APPROVER).count(),
        "admin_total": User.objects.filter(role=Role.ADMIN).count(),
        "new_users_week": User.objects.filter(date_joined__date__gte=week_ago).count(),
        # Content
        "resource_total": Resource.objects.count(),
        "resource_pending": Resource.objects.filter(status=ResourceStatus.PENDING).count(),
        "resource_approved": Resource.objects.filter(status=ResourceStatus.APPROVED).count(),
        "resource_rejected": Resource.objects.filter(status=ResourceStatus.REJECTED).count(),
        "exam_total": ExamPaper.objects.count(),
        "subject_total": Subject.objects.count(),
        # Requests & votes
        "request_open": ResourceRequest.objects.filter(status=RequestStatus.OPEN).count(),
        "request_progress": ResourceRequest.objects.filter(status=RequestStatus.IN_PROGRESS).count(),
        "request_fulfilled": ResourceRequest.objects.filter(status=RequestStatus.FULFILLED).count(),
        "vote_total": RequestVote.objects.count(),
        # Professors
        "professor_total": Professor.objects.count(),
        "rating_total": ProfessorRating.objects.count(),
        "rating_pending": ProfessorRating.objects.filter(is_approved=False).count(),
        # Study activity
        "study_sessions": study["sessions"],
        "study_minutes": study["minutes"],
        "study_minutes_today": today_minutes,
        # Misc
        "bulletin_total": Bulletin.objects.filter(is_active=True).count(),
        # Traffic & resource usage
        "traffic_today": traffic_today,
        "traffic_days": traffic_days,
        "top_modules": top_modules,
        "modules_by_semester": modules_by_semester,
        # Recent activity
        "recent_users": User.objects.order_by("-date_joined")[:8],
        "recent_resources": Resource.objects.select_related("subject", "uploader")[:8],
        "recent_requests": ResourceRequest.objects.annotate(
            votes_count=Count("votes")
        ).order_by("-created_at")[:8],
        "recent_ratings": ProfessorRating.objects.select_related("professor", "user")[:5],
        # Comments / Wall of Love
        "comment_total": GuestbookComment.objects.count(),
        "comment_pending": comment_pending,
        "comment_approved": GuestbookComment.objects.filter(is_approved=True).count(),
        "recent_comments": GuestbookComment.objects.select_related("author").order_by("-created_at")[:8],
    }

    return render(request, "manage/owner.html", context)
