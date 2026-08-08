from django.conf import settings
from django.template.loader import render_to_string

from app.models import Student, SpeechRubric, SpeechRating


def allcards(request):
    return [x for x in [peer_eval(request)] if x is not None]

def peer_eval(request):
    s: Student = request.user.student
    students = None

    rubric = SpeechRubric.get_active()

    if rubric:
        for c in s.courses.filter(year=settings.CURRENT_ACADEMIC_YEAR, semester=settings.CURRENT_SEMESTER):
            if c.type == "speech":
                students = c.students.all().order_by('fname')
                rq = list(SpeechRating.objects.filter(rubric=rubric, author=s))
                exclude = [r.speaker for r in rq]
                students = [s for s in students if s not in exclude]

    if not rubric or not students: return

    return render_to_string("app/cards/speech_eval.html", {
        "students": students,
        "rubric": rubric,
    }, request)
