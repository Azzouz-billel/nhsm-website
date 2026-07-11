from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import RatingForm
from .models import Professor, ProfessorRating

_VISIBLE = Q(ratings__is_hidden=False)


def professor_list(request):
    """All active professors with their average rating (hidden comments excluded)."""
    professors = Professor.objects.filter(is_active=True).annotate(
        avg=Avg("ratings__score", filter=_VISIBLE),
        count=Count("ratings", filter=_VISIBLE),
    )
    return render(request, "professors/list.html", {"professors": professors})


def professor_detail(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    visible = professor.ratings.filter(is_hidden=False)
    agg = visible.aggregate(avg=Avg("score"))

    my_rating = None
    is_admin = request.user.is_authenticated and request.user.is_admin
    if request.user.is_authenticated:
        my_rating = professor.ratings.filter(user=request.user).first()

    # Admins see hidden comments too (to unhide / delete); others don't.
    shown = professor.ratings.select_related("user")
    if not is_admin:
        shown = shown.filter(is_hidden=False)

    return render(
        request,
        "professors/detail.html",
        {
            "professor": professor,
            "ratings": shown,
            "avg": agg["avg"],
            "count": visible.count(),
            "my_rating": my_rating,
            "form": RatingForm(instance=my_rating),
        },
    )


@login_required
@require_POST
def rate(request, pk):
    """Create or update the signed-in student's single rating for a professor."""
    professor = get_object_or_404(Professor, pk=pk, is_active=True)
    existing = ProfessorRating.objects.filter(
        professor=professor, user=request.user
    ).first()
    form = RatingForm(request.POST, instance=existing)
    if form.is_valid():
        rating = form.save(commit=False)
        rating.professor = professor
        rating.user = request.user
        rating.save()
        messages.success(request, "Thanks — your rating was saved.")
    else:
        messages.error(request, "Please choose a score from 0 to 5.")
    return redirect("professor_detail", pk=pk)


@login_required
@require_POST
def rating_hide(request, pk):
    """Admin toggles a comment's visibility (post-moderation)."""
    if not request.user.is_admin:
        return HttpResponseForbidden("Admins only.")
    rating = get_object_or_404(ProfessorRating, pk=pk)
    rating.is_hidden = not rating.is_hidden
    rating.save(update_fields=["is_hidden"])
    return redirect("professor_detail", pk=rating.professor_id)


@login_required
@require_POST
def rating_delete(request, pk):
    """Delete a rating — allowed for an admin or the rating's own author."""
    rating = get_object_or_404(ProfessorRating, pk=pk)
    if request.user != rating.user and not request.user.is_admin:
        return HttpResponseForbidden("You can't delete this rating.")
    professor_id = rating.professor_id
    rating.delete()
    messages.success(request, "Rating removed.")
    return redirect("professor_detail", pk=professor_id)
