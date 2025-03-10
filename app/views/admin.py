from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from app.models import Course, FeatureFlag


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
