import json
from statistics import mean

from django.shortcuts import render

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


def all_evals(request):
    rub = SpeechRubric.objects.all()

    out = {}

    for r in rub:
        evals = r.speechrating_set.filter(available_to_view=False).order_by("speaker__lname")
        out[r] = evals

    return render(request, "app/speech/all_evals.html", {
        "rubrics": out
    })