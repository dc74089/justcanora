from django.template.loader import render_to_string
from django.utils import timezone

from app.models import MusicSuggestion, FeatureFlag
from app.spotify import spotify


def allcards(request):
    return [x for x in [suggestion(request), database_login(request)] if x is not None]


def suggestion(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_music_suggestion')
    if not enabled: return None

    msq = MusicSuggestion.objects.filter(student=request.user.student).order_by('-added')

    if not msq.exists() or timezone.now() - msq.first().added > timezone.timedelta(days=2, hours=12):
        return render_to_string('app/cards/music.html', request=request)


def database_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        if spotify.database_needs_login(request):
            return render_to_string('app/cards/music_spotify_db_login.html', request=request, context={
                "url": spotify.get_database_login_url(request)
            })
