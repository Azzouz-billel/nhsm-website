from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import RatingForm
from .models import Professor, ProfessorRating

# Public = approved by an admin and not later hidden.
_PUBLIC = Q(ratings__is_approved=True) & Q(ratings__is_hidden=False)


def _back(request, fallback_pk):
    """Redirect to a safe ?next (used by the admin review queue) or the professor."""
    nxt = request.POST.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("professor_detail", pk=fallback_pk)


@login_required
def professor_list(request):
    """All active professors with their average rating (approved comments only)."""
    professors = Professor.objects.filter(is_active=True).annotate(
        avg=Avg("ratings__score", filter=_PUBLIC),
        count=Count("ratings", filter=_PUBLIC),
    )
    return render(request, "professors/list.html", {"professors": professors})


@login_required
def professor_detail(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    public = professor.ratings.filter(is_approved=True, is_hidden=False)
    agg = public.aggregate(avg=Avg("score"))

    # The professor's most common tags — the "general picture".
    counter = Counter()
    for tags in public.values_list("tags", flat=True):
        counter.update(tags or [])
    top_tags = [key for key, _ in counter.most_common(5)]

    my_rating = None
    is_admin = request.user.is_authenticated and request.user.is_admin
    if request.user.is_authenticated:
        my_rating = professor.ratings.filter(user=request.user).first()

    # Admins see everything (pending + hidden) so they can moderate; a signed-in
    # student also sees their own rating (with its pending status); everyone else
    # sees only approved, non-hidden comments.
    shown = professor.ratings.select_related("user")
    if is_admin:
        pass
    elif request.user.is_authenticated:
        shown = shown.filter(
            Q(is_approved=True, is_hidden=False) | Q(user=request.user)
        )
    else:
        shown = shown.filter(is_approved=True, is_hidden=False)

    return render(
        request,
        "professors/detail.html",
        {
            "professor": professor,
            "ratings": shown,
            "avg": agg["avg"],
            "count": public.count(),
            "top_tags": top_tags,
            "my_rating": my_rating,
            "form": RatingForm(instance=my_rating),
        },
    )


@login_required
@require_POST
def rate(request, pk):
    """Create or update the student's rating — held for admin approval (pending)."""
    professor = get_object_or_404(Professor, pk=pk, is_active=True)
    existing = ProfessorRating.objects.filter(
        professor=professor, user=request.user
    ).first()
    form = RatingForm(request.POST, instance=existing)
    if form.is_valid():
        rating = form.save(commit=False)
        rating.professor = professor
        rating.user = request.user
        rating.is_approved = False  # a new or edited rating goes back to review
        rating.is_hidden = False
        rating.save()
        messages.success(
            request,
            "Thanks! Your rating was submitted and will appear once an admin reviews it.",
        )
    else:
        messages.error(request, "Please choose a score from 0 to 5.")
    return redirect("professor_detail", pk=pk)


@login_required
@require_POST
def rating_approve(request, pk):
    """Admin publishes a pending rating."""
    if not request.user.is_admin:
        return HttpResponseForbidden("Admins only.")
    rating = get_object_or_404(ProfessorRating, pk=pk)
    rating.is_approved = True
    rating.is_hidden = False
    rating.save(update_fields=["is_approved", "is_hidden"])
    return _back(request, rating.professor_id)


@login_required
@require_POST
def rating_hide(request, pk):
    """Admin toggles a comment's visibility (after it was approved)."""
    if not request.user.is_admin:
        return HttpResponseForbidden("Admins only.")
    rating = get_object_or_404(ProfessorRating, pk=pk)
    rating.is_hidden = not rating.is_hidden
    rating.save(update_fields=["is_hidden"])
    return _back(request, rating.professor_id)


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
    return _back(request, professor_id)
