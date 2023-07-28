from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import render_to_string


def allcards(request):
    return [x for x in [grade(request), bday(request)] if x is not None]


def grade(request):
    if request.user.student.grade is None:
        return render_to_string('common/cards/grade.html', request=request)


def bday(request):
    if request.user.student.bday is None:
        return render_to_string('common/cards/bday.html', request=request)
