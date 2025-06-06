from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from app.models import MusicSuggestion, Course, ApprovedSong
from app.spotify import spotify, playlists, nowplaying
from app.spotify.search import search


def get_now_playing(request):
    if not nowplaying.now_playing_available(request):
        return HttpResponse("There was a problem")

    now_playing = nowplaying.get_now_playing(request)

    if not now_playing or not now_playing['item']:
        return HttpResponse("Nothing is playing")

    return HttpResponse(
        f"Now Playing: <b>{now_playing['item']['name']}</b> by <b>{now_playing['item']['artists'][0]['name']}</b>")


def get_now_playing_json(request):
    if not nowplaying.now_playing_available(request, check_auth=False):
        return JsonResponse({
            "title": "There Was a Problem",
            "artist": "There Was a Problem"
        })

    now_playing = nowplaying.get_now_playing(request)

    if not now_playing or not now_playing['item']:
        return JsonResponse({
            "title": "Nothing is Playing",
            "artist": "Nothing is Playing"
        })

    return JsonResponse({
        "title": now_playing['item']['name'],
        "artist": now_playing['item']['artists'][0]['name']
    })


def get_next_song_json(request):
    if not nowplaying.now_playing_available(request, check_auth=False):
        return JsonResponse({
            "title": "There Was a Problem",
            "artist": "There Was a Problem"
        })

    next = nowplaying.get_next_track(request)

    if not next:
        return JsonResponse({
            "title": "Nothing is Playing",
            "artist": "Nothing is Playing"
        })

    return JsonResponse({
        "title": next['name'],
        "artist": next['artists'][0]['name']
    })


@csrf_exempt
def do_play_pause(request):
    if request.headers.get('key', "") == 'oinkoinkboom':
        nowplaying.play_pause(request)

        return HttpResponse(status=200)

    return HttpResponseBadRequest()


@csrf_exempt
def do_skip(request):
    if request.headers.get('key', "") == 'oinkoinkboom':
        nowplaying.next_track(request)

        return HttpResponse(status=200)

    return HttpResponseBadRequest()


@staff_member_required
def music_queue(request):
    if spotify.needs_login(request):
        request.session['next'] = 'music_queue'
        request.session.save()

        return redirect(spotify.get_login_url(request))

    sugs = MusicSuggestion.objects.filter(investigated=False).exclude(spotify_uri__isnull=True).exclude(spotify_uri="")

    for sug in sugs:
        sug.data = sug.get_spotify_data(request)

    sugs = [sug for sug in sugs if sug.student.is_active(enforce_semester=True)]

    return render(request, "app/admin/music_queue.html", {
        "suggestions": sugs
    })


@staff_member_required
@csrf_exempt
def all_approved_songs(request):
    if request.method == "GET":
        songs = list(ApprovedSong.objects.all())

        for song in songs:
            song.data = song.get_spotify_data(request)

        songs.sort(key=lambda x: x.data['artists'][0]['name'].lower() + " - " + x.data['name'].lower())

        return render(request, "app/admin/music_approved.html", {
            "songs": songs
        })
    elif request.method == "POST":
        if request.POST.get("action", "") == "remove_approved_song" and 'uri' in request.POST:
            song = ApprovedSong.objects.get(spotify_uri=request.POST['uri'])
            song.delete()

            return HttpResponse(status=200)
    return HttpResponseBadRequest()


@staff_member_required
def search_table(request):
    q = request.GET.get('q')

    if not q: return HttpResponseBadRequest()

    results = search(request, q)

    return render(request, 'app/admin/music_partial_table.html', {
        'songs': results['tracks']['items']
    })


@csrf_exempt
@staff_member_required
def queue_song(request):
    if 'id' in request.POST:
        sug = MusicSuggestion.objects.get(id=request.POST['id'])
        nowplaying.queue_by_uri(request, sug.spotify_uri)
    if 'uri' in request.POST:
        nowplaying.queue_by_uri(request, request.POST['uri'])

    return HttpResponse(status=200)


def add_song_helper(request, sug_id):
    """
    Adds a song to all applicable playlists.
    Separated from the View function so it can be automatically called when songs are already marked clean
    """

    sug = MusicSuggestion.objects.get(id=sug_id)

    courses = sug.student.courses.filter(
        year=settings.CURRENT_ACADEMIC_YEAR,
        semester=settings.CURRENT_SEMESTER
    ) | sug.student.courses.filter(
        year=settings.CURRENT_ACADEMIC_YEAR,
        name__contains="YR"
    )

    if sug.for_playlist:
        for c in courses:
            if not c.playlist_id:
                plid = playlists.create_playlist(request, c.name)
                c.playlist_id = plid
                c.save()

            playlists.add_song_to_playlist(request, c.playlist_id, sug.spotify_uri)
    else:
        playlists.add_song_to_playlist(request, settings.PERSONAL_SPOTIFY_PLAYLIST, sug.spotify_uri)

    sug.investigated = True
    sug.is_rejected = False
    sug.investigated_date = timezone.now()
    sug.save()


@csrf_exempt
@staff_member_required
def add_song(request):
    if request.method != "POST": return HttpResponseBadRequest()

    data = request.POST

    if 'id' not in data: return HttpResponseBadRequest()

    add_song_helper(request, int(data['id']))

    sug = MusicSuggestion.objects.get(id=data['id'])
    ApprovedSong.objects.get_or_create(spotify_uri=sug.spotify_uri)

    return HttpResponse(status=200)


@csrf_exempt
@staff_member_required
def deny_song(request):
    if 'id' in request.POST:
        sug = MusicSuggestion.objects.get(id=request.POST['id'])
        sug.investigated = True
        sug.is_rejected = True
        sug.save()

    return HttpResponse(status=200)
