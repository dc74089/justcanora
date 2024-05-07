from django.http import HttpResponse

from app.models import FeatureFlag
from app.spotify import spotify


def now_playing_available(request):
    try:
        logged_in = request.user.is_authenticated
        flag, _ = FeatureFlag.objects.get_or_create(id="fab_now_playing")

        return logged_in and flag and not spotify.needs_login(request)
    except:
        return False


def context_processor(request):
    return {
        "now_playing_available": now_playing_available(request)
    }


def get_now_playing(request):
    return spotify.get_spotify(request).currently_playing()


def queue_by_uri(request, uri):
    spotify.get_spotify(request).add_to_queue(uri)
