from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render

from app.models import Student
from .models import Wrapped, TeacherWrapped


def wrapped(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    if not Wrapped.objects.filter(student=request.user.student).exists():
        return HttpResponseBadRequest()

    return render(request, 'wrapped/wrapped2025.html', {
        'data': Wrapped.objects.get(student=request.user.student)
    })


@staff_member_required
def ranks(request):
    all = Wrapped.objects.all()

    out = {
        "Songs": Wrapped.objects.all().order_by('rank_songs'),
        "Assignments": Wrapped.objects.all().order_by('rank_assignments'),
        "Late": Wrapped.objects.all().order_by('rank_late'),
        "Minutes": Wrapped.objects.all().order_by('rank_canvas_minutes'),
        "Clicks": Wrapped.objects.all().order_by('rank_canvas_clicks'),
    }

    return render(request, "wrapped/ranks.html", {
        "data": out
    })


@staff_member_required
def student_data(request):
    return render(request, "wrapped/student_data.html", {
        "data": Wrapped.objects.all().order_by('student__fname')
    })


@staff_member_required
def teacher_data(request):
    return render(request, "wrapped/teacher_data.html", {
        "data": TeacherWrapped.objects.all().order_by('name')
    })


def wrapped_teacher(request, key):
    tw = TeacherWrapped.objects.get(key=key)

    return render(request, 'wrapped/teacherwrapped2025.html', {
        'data': tw,
        'now_playing_available': False
    })


def wrapped_demo(request):
    if 'student' in request.GET:
        return render(request, 'wrapped/wrapped2025.html', {
            'data': Wrapped.objects.get(student=Student.objects.get(id=int(request.GET['student']))),
            'now_playing_available': False
        })
    else:
        return render(request, 'wrapped/wrapped2025.html', {
            'data': Wrapped.objects.get(student=Student.objects.get(id=11339)),
            'now_playing_available': False
        })


def wrapped_teacher_demo(request):
    return render(request, 'wrapped/teacherwrapped2025.html', {
        'data': TeacherWrapped.objects.get(teacher_id=11862),
        'now_playing_available': False
    })
