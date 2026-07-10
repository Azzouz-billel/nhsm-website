from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from rest_framework.generics import ListAPIView

from .forms import ResourceUploadForm
from .models import (
    ExamPaper,
    ExamType,
    Resource,
    ResourceStatus,
    ResourceType,
    Speciality,
    Subject,
)
from .serializers import ExamPaperSerializer, ResourceSerializer


# One rotates onto the home page each day (indexed by day-of-year), so the
# whole cohort sees the same "quote of the day".
STUDY_QUOTES = [
    ("Pure mathematics is, in its way, the poetry of logical ideas.", "Albert Einstein"),
    ("Mathematics is the music of reason.", "James Joseph Sylvester"),
    ("The essence of mathematics lies in its freedom.", "Georg Cantor"),
    ("Do not worry about your difficulties in mathematics. I can assure you mine are still greater.", "Albert Einstein"),
    ("It is not knowledge, but the act of learning, that grants the greatest enjoyment.", "Carl Friedrich Gauss"),
    ("Mathematics is not about numbers, but about understanding.", "William Paul Thurston"),
    ("A mathematician who is not also something of a poet will never be a complete mathematician.", "Karl Weierstrass"),
    ("Nature is written in the language of mathematics.", "Galileo Galilei"),
    ("Mathematics knows no races or geographic boundaries.", "David Hilbert"),
    ("Logic is the anatomy of thought.", "John Locke"),
    ("Genius is one percent inspiration and ninety-nine percent perspiration.", "Thomas Edison"),
    ("The only way to learn mathematics is to do mathematics.", "Paul Halmos"),
    ("Small is the number of people who see with their eyes and think with their minds.", "Albert Einstein"),
    ("An equation for me has no meaning unless it expresses a thought of God.", "Srinivasa Ramanujan"),
    ("Somewhere, something incredible is waiting to be known.", "Carl Sagan"),
    ("What we know is a drop, what we don't know is an ocean.", "Isaac Newton"),
    ("The moving power of mathematical invention is not reasoning but imagination.", "Augustus De Morgan"),
    ("Obvious is the most dangerous word in mathematics.", "E. T. Bell"),
    ("Mathematics is the queen of the sciences.", "Carl Friedrich Gauss"),
    ("If people do not believe that mathematics is simple, it is only because they do not realize how complicated life is.", "John von Neumann"),
    ("Perseverance is not a long race; it is many short races one after the other.", "Walter Elliot"),
    ("Success is the sum of small efforts repeated day in and day out.", "Robert Collier"),
    ("The more I study, the more insatiable do I feel my genius for it to be.", "Ada Lovelace"),
    ("Errors, like straws, upon the surface flow; who would search for pearls must dive below.", "John Dryden"),
]


def home(request):
    """Landing page with a snapshot of the library."""
    approved = Resource.objects.filter(status=ResourceStatus.APPROVED)
    day = timezone.localdate().timetuple().tm_yday
    text, author = STUDY_QUOTES[day % len(STUDY_QUOTES)]
    context = {
        "resource_count": approved.count() + ExamPaper.objects.count(),
        "subject_count": Subject.objects.count(),
        "semester_count": Subject.objects.values("semester").distinct().count(),
        "chargily_url": settings.CHARGILY_DONATION_URL,
        "redotpay_url": settings.REDOTPAY_DONATION_URL,
        "quote_text": text,
        "quote_author": author,
    }
    return render(request, "home.html", context)


def about(request):
    """Intro to NHSM for newcomers: fields, faculty, campus life, student reps."""
    # Auto-discover the rotating campus photos so the owner can add/remove any
    # number by dropping `nhsm-slide-*` files into static/img.
    slide_dir = settings.STATICFILES_DIRS[0] / "img"
    about_slides = [
        f"img/{path.name}" for path in sorted(slide_dir.glob("nhsm-slide-*"))
    ]
    return render(
        request,
        "about.html",
        {"specialities": Speciality.choices, "about_slides": about_slides},
    )


def contact(request):
    """Static contact page — who made the site and how to reach them."""
    return render(request, "contact.html")


def resource_library(request):
    """Filterable catalogue. Results are loaded client-side from the search API."""
    subjects = (
        Subject.objects.annotate(
            approved_count=Count(
                "resources",
                filter=Q(resources__status=ResourceStatus.APPROVED),
            )
        )
        .filter(approved_count__gt=0)
        .order_by("semester", "name")
    )
    semesters = sorted({s.semester for s in subjects})
    context = {
        "subjects": subjects,
        "semesters": semesters,
        "resource_types": ResourceType.choices,
        "specialities": Speciality.choices,
    }
    return render(request, "resources/library.html", context)


@login_required
def upload_resource(request):
    """Let signed-in students submit a resource; it enters the pending queue."""
    if request.method == "POST":
        form = ResourceUploadForm(request.POST)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.uploader = request.user
            resource.status = ResourceStatus.PENDING
            resource.save()
            messages.success(
                request, "Thanks! Your resource was submitted for review."
            )
            return redirect("resource_library")
    else:
        form = ResourceUploadForm()
    return render(request, "resources/upload.html", {"form": form})


class ResourceSearchAPIView(ListAPIView):
    """JSON search over approved resources, filtered by semester / subject / type / text."""

    serializer_class = ResourceSerializer

    def get_queryset(self):
        qs = Resource.objects.filter(status=ResourceStatus.APPROVED).select_related(
            "subject"
        )
        params = self.request.query_params

        semester = params.get("semester")
        if semester:
            qs = qs.filter(subject__semester=semester)

        subject = params.get("subject")
        if subject:
            qs = qs.filter(subject__slug=subject)

        speciality = params.get("speciality")
        if speciality:
            qs = qs.filter(subject__speciality=speciality)

        resource_type = params.get("type")
        if resource_type:
            qs = qs.filter(resource_type=resource_type)

        query = params.get("q")
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(subject__name__icontains=query)
            )

        return qs


def annales(request):
    """Past-exams archive — a separate section browsable by year/semester/module/type."""
    subjects = (
        Subject.objects.annotate(exam_count=Count("exam_papers"))
        .filter(exam_count__gt=0)
        .order_by("semester", "name")
    )
    years = (
        ExamPaper.objects.values_list("year", flat=True).distinct().order_by("-year")
    )
    context = {
        "subjects": subjects,
        "semesters": sorted({s.semester for s in subjects}),
        "years": list(years),
        "exam_types": ExamType.choices,
        "specialities": Speciality.choices,
    }
    return render(request, "resources/annales.html", context)


class ExamSearchAPIView(ListAPIView):
    """JSON search over exam papers, filtered by year / semester / subject / type / text."""

    serializer_class = ExamPaperSerializer

    def get_queryset(self):
        qs = ExamPaper.objects.select_related("subject")
        params = self.request.query_params

        year = params.get("year")
        if year:
            qs = qs.filter(year=year)

        semester = params.get("semester")
        if semester:
            qs = qs.filter(subject__semester=semester)

        subject = params.get("subject")
        if subject:
            qs = qs.filter(subject__slug=subject)

        speciality = params.get("speciality")
        if speciality:
            qs = qs.filter(subject__speciality=speciality)

        exam_type = params.get("type")
        if exam_type:
            qs = qs.filter(exam_type=exam_type)

        if params.get("solution") == "1":
            qs = qs.filter(has_solution=True)

        query = params.get("q")
        if query:
            qs = qs.filter(
                Q(title__icontains=query) | Q(subject__name__icontains=query)
            )

        return qs
