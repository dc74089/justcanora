from django.template.loader import render_to_string

from app.models import WebserverCredential


def allcards(request):
    return [x for x in [instructions(request)] if x is not None]


def instructions(request):
    if WebserverCredential.objects.filter(student=request.user.student).exists():
        return render_to_string("app/cards/webserver_view_instructions.html", request=request)
