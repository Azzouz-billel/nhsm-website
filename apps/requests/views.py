from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import Count
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import RequestForm
from .models import RequestStatus, RequestVote, ResourceRequest


def board(request):
    """List requests (most-upvoted first) and let signed-in users post new ones."""
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        form = RequestForm(request.POST)
        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.author = request.user
            new_request.save()
            messages.success(request, "Your request was posted.")
            return redirect("request_board")
    else:
        form = RequestForm()

    active_status = request.GET.get("status", "")
    requests_qs = (
        ResourceRequest.objects.select_related("subject", "author")
        .annotate(votes_count=Count("votes"))
        .order_by("-votes_count", "-created_at")
    )
    if active_status in RequestStatus.values:
        requests_qs = requests_qs.filter(status=active_status)

    voted_ids = set()
    if request.user.is_authenticated:
        voted_ids = set(
            RequestVote.objects.filter(user=request.user).values_list(
                "request_id", flat=True
            )
        )

    return render(
        request,
        "requests/board.html",
        {
            "form": form,
            "requests": requests_qs,
            "voted_ids": voted_ids,
            "statuses": RequestStatus.choices,
            "active_status": active_status,
        },
    )


@login_required
@require_POST
def vote(request, pk):
    """Toggle the current user's vote (one per request, enforced by the model)."""
    resource_request = get_object_or_404(ResourceRequest, pk=pk)
    existing, created = RequestVote.objects.get_or_create(
        user=request.user, request=resource_request
    )
    if not created:
        existing.delete()
    count = resource_request.votes.count()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"voted": created, "count": count})
    return redirect("request_board")


@login_required
@require_POST
def update_status(request, pk):
    """Author or an approver moves a request through Open → In progress → Fulfilled."""
    resource_request = get_object_or_404(ResourceRequest, pk=pk)
    if request.user != resource_request.author and not request.user.is_approver:
        return HttpResponseForbidden("You can't change this request.")

    status = request.POST.get("status")
    if status in RequestStatus.values:
        resource_request.status = status
        resource_request.fulfilled_link = request.POST.get("fulfilled_link", "").strip()
        resource_request.save(update_fields=["status", "fulfilled_link"])
        messages.success(request, "Request updated.")
    return redirect("request_board")
