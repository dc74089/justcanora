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
