from django.template.loader import render_to_string
from django.utils import timezone

from spotipy.oauth2 import SpotifyOauthError

from app.models import MusicSuggestion, FeatureFlag
from app.spotify import spotify


def allcards(request):
    try:
        return [x for x in [suggestion(request), login(request), expiring_soon(request)] if x is not None]
    except SpotifyOauthError:
        return []


def suggestion(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_music_suggestion')
    free_for_all, _ = FeatureFlag.objects.get_or_create(id='card_music_unlimited')

    if not enabled: return None

    msq = MusicSuggestion.objects.filter(student=request.user.student).order_by('-added')

    if (free_for_all
            or request.user.student.id == 102798
            or not msq.exists()
            or timezone.now() - msq.first().added > timezone.timedelta(days=0, hours=12)):
        return render_to_string('app/cards/music.html', request=request)


def login(request):
    if request.user.is_authenticated and request.user.is_staff:
        if spotify.needs_login(request):
            return render_to_string('app/cards/music_spotify_db_login.html', request=request, context={
                "url": spotify.get_login_url(request)
            })


def expiring_soon(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_music_suggestion')
    if not enabled: return None

    msq = MusicSuggestion.objects.filter(student=request.user.student).order_by('-added')

    if not (request.user.student.id == 102798
            or not msq.exists()
            or timezone.now() - msq.first().added > timezone.timedelta(days=2, hours=12)):
        return None

    s = request.user.student

    reqs = MusicSuggestion.objects.filter(
        student__courses__in=s.courses.all(),
        for_playlist=True,
        is_rejected=False,
        investigated=True
    ).distinct()

    reqs_out = []

    for req in reqs:
        if req.is_expiring_soon():
            keep = True
            # Remove entry if there is a valid suggestion for that song
            for req2 in MusicSuggestion.objects.filter(
                    spotify_uri=req.spotify_uri,
                    student__courses__in=s.courses.all(),
                    investigated=True):
                if not req2.is_expiring_soon():
                    keep = False

            if keep:
                req.data = req.get_spotify_data(request)
                reqs_out.append(req)

    if len(reqs_out) > 0:
        return render_to_string('app/cards/music_expiring_soon.html', request=request, context={
            "reqs": reqs_out
        })
    else:
        return None
