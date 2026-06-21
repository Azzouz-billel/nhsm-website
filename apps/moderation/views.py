from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.resources.models import Resource, ResourceStatus


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
