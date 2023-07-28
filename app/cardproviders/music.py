from django.template.loader import render_to_string
from django.utils import timezone

from app.models import MusicSuggestion


def allcards(request):
    return [x for x in [suggestion(request)] if x is not None]


def suggestion(request):
    msq = MusicSuggestion.objects.filter(student=request.user.student).order_by('-added')

    if not msq.exists() or timezone.now() - msq.first().added > timezone.timedelta(days=2, hours=12):
        return render_to_string('app/cards/music.html', request=request)
