from django.template.loader import render_to_string
from django.utils import timezone

from app.models import MusicSuggestion, FeatureFlag


def allcards(request):
    return [x for x in [suggestion(request)] if x is not None]


def suggestion(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_music_suggestion')

    if not enabled: return None

    msq = MusicSuggestion.objects.filter(student=request.user.student).order_by('-added')

    if not msq.exists() or timezone.now() - msq.first().added > timezone.timedelta(days=2, hours=12):
        return render_to_string('app/cards/music.html', request=request)
