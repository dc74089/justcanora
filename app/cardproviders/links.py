from django.template.loader import render_to_string

from app.models import WebserverCredential, Student, SpeechRubric


def allcards(request):
    return [x for x in [links(request)] if x is not None]


def links(request):
    s: Student = request.user.student

    ctx = {}

    if SpeechRubric.objects.filter(available_to_view=True, speechrating__speaker=s):
        ctx['evals'] = True

    if WebserverCredential.objects.filter(student=request.user.student).exists():
        ctx['creds'] = WebserverCredential.objects.filter(student=request.user.student).first()

    if ctx:
        return render_to_string("app/cards/links.html", ctx, request)
