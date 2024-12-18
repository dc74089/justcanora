from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from app.models import Student, FeatureFlag, Wrapped


def allcards(request):
    return [x for x in [wrapped2024(request), bday_self(request), bday_others(request)] if x is not None]


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

    bq = Student.objects.filter(
        bday__month=now.month,
        bday__day=now.day,
        courses__in=student.courses.all()
    ).exclude(
        id=student.id
    )

    blist = [s for s in bq if s.is_active()]

    if blist:
        return render_to_string("app/cards/happy_bday_others.html",
                                {"students": bq},
                                request=request)
    else:
        return None


def wrapped2024(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_wrapped')

    if enabled and Wrapped.objects.filter(student=request.user.student).exists():
        return render_to_string("app/cards/wrapped.html", request=request)
