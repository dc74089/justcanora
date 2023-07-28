from django.template.loader import render_to_string


def allcards(request):
    return [x for x in [grade(request), bday(request)] if x is not None]


def grade(request):
    if request.user.student.grade is None:
        return render_to_string('app/cards/grade.html', request=request)


def bday(request):
    if request.user.student.bday is None:
        return render_to_string('app/cards/bday.html', request=request)
