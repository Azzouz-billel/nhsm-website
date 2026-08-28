from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.resources.models import Resource, ResourceStatus
from config.throttle import rate_limit

from .forms import GuestbookCommentForm


def _is_approver(user):
    return user.is_authenticated and user.is_approver


# Redirects anonymous and non-approver users to the login page.
approver_required = user_passes_test(_is_approver)


@approver_required
def queue(request):
    pending = (
        Resource.objects.filter(status=ResourceStatus.PENDING)
        .select_related("subject", "uploader")
        .order_by("created_at")
    )
    return render(request, "moderation/queue.html", {"pending": pending})


@require_POST
@approver_required
def review(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    action = request.POST.get("action")
    if action == "approve":
        resource.approve(by_user=request.user)
        messages.success(request, f"Approved “{resource.title}”.")
    elif action == "reject":
        resource.reject(by_user=request.user)
        messages.success(request, f"Rejected “{resource.title}”.")
    return redirect("moderation_queue")


@require_POST
@login_required
@rate_limit("comment", 5, 3600)
def comment_add(request):
    """A signed-in member leaves a note for the home page wall.

    Always created unapproved — it only shows publicly once an admin
    approves it from the manage area.
    """
    form = GuestbookCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.is_approved = False
        comment.is_pinned = False
        comment.save()
        messages.success(
            request, "Thanks! Your comment appears after a quick review."
        )
    else:
        first_error = form.errors.get("text", ["That comment didn't look right — keep it under 280 characters."])[0]
        messages.error(request, first_error)
    return redirect("home")
