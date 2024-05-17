from django.template.loader import render_to_string

from app.models import WebserverCredential, Student, SpeechRubric, FeatureFlag


def allcards(request):
    return [x for x in [links(request)] if x is not None]


def links(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_links')

    if enabled:
        s: Student = request.user.student

        ctx = {}

        if SpeechRubric.objects.filter(available_to_view=True, speechrating__speaker=s):
            ctx['evals'] = True

        if WebserverCredential.objects.filter(student=request.user.student).exists():
            ctx['creds'] = WebserverCredential.objects.filter(student=request.user.student).first()

        if ctx:
            return render_to_string("app/cards/links.html", ctx, request)
