from django.template.loader import render_to_string

from app.models import Student, FeatureFlag, SpeechRubric


def allcards(request):
    return [x for x in [peer_eval(request)] if x is not None]


def peer_eval(request):
    s: Student = request.user.student
    rubric = None
    students = None

    flag, _ = FeatureFlag.objects.get_or_create(id="card_speech")

    if flag:
        rubric_name = flag.get_config().get("rubric_name")
        rubric = SpeechRubric.objects.get(speech=rubric_name)

    for c in s.courses.all():
        if c.type == "speech":
            students = c.students.all().order_by('fname')

    if not students or not rubric: return

    return render_to_string("app/cards/speech_eval.html", {
        "students": students,
        "rubric": rubric,
    }, request)
