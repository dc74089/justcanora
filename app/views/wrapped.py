from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render

from app.models import Wrapped2024, Student


def wrapped2024(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    if not Wrapped2024.objects.filter(student=request.user.student).exists():
        return HttpResponseBadRequest()

    return render(request, 'app/wrapped/wrapped2024.html', {
        'data': Wrapped2024.objects.get(student=request.user.student)
    })


def wrapped_demo(request):
    return render(request, 'app/wrapped/wrapped2024.html', {
        'data': Wrapped2024.objects.get(student=Student.objects.get(id=3432))
    })