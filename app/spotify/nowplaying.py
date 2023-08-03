from django.http import HttpResponse

from app.models import FeatureFlag
from app.spotify import spotify


def now_playing_available(request):
    logged_in = request.user.is_authenticated
    flag, _ = FeatureFlag.objects.get_or_create(id="fab_now_playing")
    needs_login = spotify.database_needs_login(request)

    return logged_in and flag and not needs_login


def context_processor(request):
    return {
        "now_playing_available": now_playing_available(request)
    }


def get_now_playing(request):
    return spotify.get_spotify(request, use_session=False).currently_playing()
