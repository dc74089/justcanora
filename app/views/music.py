from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from app.models import Course, MusicSuggestion
from app.spotify import spotify, playlists, nowplaying
from app.spotify.search import search


def get_now_playing(request):
    if not nowplaying.now_playing_available(request):
        return HttpResponse("There was a problem")

    now_playing = nowplaying.get_now_playing(request)

    if not now_playing or not now_playing['item']:
        return HttpResponse("Nothing is playing")

    return HttpResponse(f"Now Playing: <b>{now_playing['item']['name']}</b> by <b>{now_playing['item']['artists'][0]['name']}</b>")


@staff_member_required
def music_queue(request):
    if spotify.session_needs_login(request):
        request.session['next'] = 'music_queue'
        request.session.save()

        return redirect(spotify.get_session_login_url(request))

    return render(request, 'app/admin/music_queue.html', {
        "courses": Course.objects.all().order_by('semester', 'period'),
        "suggestions": {
            course.id: MusicSuggestion.objects.filter(
                student__courses=course,
                investigated=False,
                for_playlist=True
            ) for course in Course.objects.all()
        }
    })


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
def add_song(request):
    if request.method != "POST": return HttpResponseBadRequest()

    data = request.POST

    if 'suggestion' not in data or 'song' not in data: return HttpResponseBadRequest()

    sug = MusicSuggestion.objects.get(id=int(data['suggestion']))

    courses = sug.student.courses.all()

    for c in courses:
        if not c.playlist_id:
            plid = playlists.create_playlist(request, c.name)
            c.playlist_id = plid
            c.save()

        playlists.add_song_to_playlist(request, c.playlist_id, data['song'])

    sug.spotify_uri = data['song']
    sug.investigated = True
    sug.save()

    return HttpResponse(status=200)
