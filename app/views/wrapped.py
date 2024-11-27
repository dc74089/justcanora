from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render

from app.models import Wrapped2025, Student


def wrapped2024(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    if not Wrapped2025.objects.filter(student=request.user.student).exists():
        return HttpResponseBadRequest()

    return render(request, 'app/wrapped/wrapped2025.html', {
        'data': Wrapped2025.objects.get(student=request.user.student)
    })


def teacher_wrapped_2025(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()


def wrapped_demo(request):
    if 'student' in request.GET:
        return render(request, 'app/wrapped/wrapped2025.html', {
            'data': Wrapped2025.objects.get(student=Student.objects.get(id=int(request.GET['student']))),
            'now_playing_available': False
        })
    else:
        return render(request, 'app/wrapped/wrapped2025.html', {
            'data': Wrapped2025.objects.get(student=Student.objects.get(id=3432)),
            'now_playing_available': False
        })
