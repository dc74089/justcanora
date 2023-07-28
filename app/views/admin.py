from django.conf import settings
from django.shortcuts import render

from app.models import Course


def admin(request):
    return render(request, 'app/admin/admin.html')


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
