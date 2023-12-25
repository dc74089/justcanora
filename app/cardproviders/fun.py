from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from app.models import Student


def allcards(request):
    return [x for x in [bday_self(request), bday_others(request)] if x is not None]


def bday_self(request):
    bday = request.user.student.bday
    now = timezone.now().astimezone(settings.EST).date()

    if not bday: return None

    if bday.month == now.month and bday.day == now.day:
        return render_to_string("app/cards/happy_bday_self.html", request=request)


def bday_others(request):
    student: Student = request.user.student
    now = timezone.now().astimezone(settings.EST).date()

    if not student.courses: return None

    bq = Student.objects.filter(bday__month=now.month, bday__day=now.day, courses__in=student.courses.all()).exclude(
        id=student.id)

    if bq.exists():
        return render_to_string("app/cards/happy_bday_others.html",
                                {"students": bq},
                                request=request)
    else:
        return None
