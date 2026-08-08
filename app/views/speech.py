import json
from statistics import mean

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from app.models import SpeechRubric, Student, SpeechRating


def view_evals(request):
    if request.user.is_staff and "stu" in request.GET:
        s = Student.objects.get(id=request.GET['stu'])
        srq = SpeechRubric.objects.filter(speechrating__speaker=s)
    else:
        s: Student = request.user.student
        srq = SpeechRubric.objects.filter(available_to_view=True, speechrating__speaker=s)

    students = Student.objects.filter(courses__type="speech").order_by("lname").distinct()

    out = {}

    for rub in srq:
        out[rub] = {}
        ratings = {}
        comments = {}

        for evl in SpeechRating.objects.filter(rubric=rub, speaker=s, available_to_view=True):
            data = json.loads(evl.data)

            for field in data.get("rating", []):
                if field not in ratings:
                    ratings[field] = []

                ratings[field].append(float(data['rating'][field]))

            for field in data.get("comment", []):
                if field not in comments:
                    comments[field] = []

                comments[field].append(data['comment'][field])

        out[rub]['ratings'] = {x: mean(ratings[x]) * 20 for x in ratings}
        out[rub]['comments'] = comments

    return render(request, "app/speech/view_evals.html", {
        "evals": out,
        "students": students
    })


@staff_member_required
def rubrics(request):
    """One place to pick what students are evaluating and what they can read back."""
    active = SpeechRubric.get_active()

    counted = SpeechRubric.objects.annotate(
        total=Count('speechrating'),
        approved=Count('speechrating', filter=Q(speechrating__available_to_view=True)),
        speakers=Count('speechrating__speaker', distinct=True, filter=Q(speechrating__available_to_view=True)),
    ).order_by('id')

    rows = [{
        "rubric": rub,
        "active": active is not None and rub.id == active.id,
        "approved": rub.approved,
        "pending": rub.total - rub.approved,
        "speakers": rub.speakers,
    } for rub in counted]

    return render(request, "app/speech/rubrics.html", {
        "rows": rows,
        "active": active,
        "pending": sum(row["pending"] for row in rows),
        "published": sum(1 for row in rows if row["rubric"].available_to_view),
    })


@staff_member_required
@require_POST
def set_active(request):
    """Start collecting peer evals for a rubric, or stop collecting entirely."""
    starting = request.POST['active'] == "true"
    SpeechRubric.set_active(SpeechRubric.objects.get(id=request.POST['rubric']) if starting else None)

    return HttpResponse(status=200)


@staff_member_required
@require_POST
def set_published(request):
    """Publishing a rubric lets its speakers read their (approved) evals."""
    rubric = SpeechRubric.objects.get(id=request.POST['rubric'])
    rubric.available_to_view = request.POST['published'] == "true"
    rubric.save()

    return HttpResponse(status=200)


@staff_member_required
def all_evals(request):
    sections = []

    for rub in SpeechRubric.objects.order_by('id'):
        evals = (rub.speechrating_set
                 .filter(available_to_view=False)
                 .select_related('author', 'speaker')
                 .order_by("speaker__lname"))

        if evals:
            sections.append({"rubric": rub, "evals": evals, "pending": len(evals)})

    return render(request, "app/speech/all_evals.html", {
        "sections": sections,
        "pending": sum(section["pending"] for section in sections),
    })


@staff_member_required
@require_POST
def approve_rating(request):
    SpeechRating.objects.filter(id=request.POST['id']).update(available_to_view=True)

    return HttpResponse(status=200)


@staff_member_required
@require_POST
def approve_all(request):
    """Approve every outstanding eval on one rubric — the common case once you've skimmed them."""
    SpeechRating.objects.filter(rubric_id=request.POST['rubric']).update(available_to_view=True)

    return HttpResponse(status=200)
