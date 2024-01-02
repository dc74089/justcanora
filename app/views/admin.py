from pprint import pprint

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from app.models import Course, FeatureFlag, MusicSuggestion, DataCollectionQuestion
from app.spotify import spotify


@staff_member_required
def admin(request):
    flags = FeatureFlag.objects.all()

    return render(request, 'app/admin/admin.html', {
        "flags": flags
    })


@csrf_exempt
@staff_member_required
def set_flag(request):
    if request.method != 'POST': return HttpResponseBadRequest()

    data = request.POST

    if 'flag' not in data or 'status' not in data: return HttpResponseBadRequest()

    flag = FeatureFlag.objects.get(id=data['flag'])
    flag.enabled = data['status'] == "true"
    flag.save()

    return HttpResponse(status=200)


@staff_member_required
def rosters(request):
    s1 = []
    s2 = []
    for c in Course.objects.filter(year=settings.CURRENT_ACADEMIC_YEAR).order_by('period'):
        if c.semester == 1:
            s1.append(c)
        elif c.semester == 2:
            s2.append(c)
        else:
            s1.append(c)
            s2.append(c)

    return render(request, "app/admin/rosters.html", {
        "semesters": (s1, s2)
    })


@staff_member_required
def view_answers(request):
    questions = list(DataCollectionQuestion.objects.all())

    if request.GET.get('question'):
        q = DataCollectionQuestion.objects.get(id=request.GET['question'])
        answers = q.answers.all()

        ans_dict = {}
        out = []

        for ans in answers:
            for course in ans.student.courses.all():
                if course not in ans_dict:
                    ans_dict[course] = []

                ans_dict[course].append(ans)

        for course in sorted(ans_dict.keys(), key=lambda x: str(x.semester) + str(x.period)):
            out.append((course, sorted(ans_dict[course], key=lambda x: x.student.fname)))

        return render(request, 'app/admin/datacollection_answers.html', {
            "questions": questions,
            "answers": out
        })
    else:
        return render(request, 'app/admin/datacollection_answers.html', {
            "questions": questions
        })
