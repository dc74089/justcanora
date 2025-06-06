from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render

from app.models import MusicSuggestion, Course, Student, SpeechRating, SpeechRubric, ApprovedSong
from app.spotify.search import search
from app.views.music import add_song_helper


def misc_action(request):
    if request.method == 'POST':
        data = request.POST

        if 'action' not in data: return HttpResponseBadRequest()

        if data['action'] == 'setgrade':
            s = request.user.student
            s.grade = int(data['grade'])
            s.save()
        elif data['action'] == 'setbday':
            s = request.user.student
            s.bday = data['bday']
            s.save()
        elif data['action'] == 'music':
            ms = MusicSuggestion(
                student=request.user.student,
                song=data['song_name'],
                artist=data['song_artist'],
                for_playlist=data['song_type'] == 'class',
                spotify_uri=data['uri']
            )
            ms.save()

            approved_song = ApprovedSong.objects.filter(
                spotify_uri=ms.spotify_uri
            )

            if approved_song.exists():
                add_song_helper(request, ms.id)

        elif data['action'] == 'music_rescue':
            old = MusicSuggestion.objects.get(id=data['req_id'])

            ms = MusicSuggestion(
                student=request.user.student,
                song=old.song,
                artist=old.artist,
                for_playlist=True,
                spotify_uri=old.spotify_uri,
                investigated=True
            )
            ms.save()
        elif data['action'] == 'speech_eval':
            speaker = Student.objects.get(id=data['speaker'])
            rubric = SpeechRubric.objects.get(id=data['rubric'])

            sr = SpeechRating(
                speaker=speaker,
                author=request.user.student,
                rubric=rubric
            )

            sr.save()

            ratings = {
                "rating": {rat[1]: data[rat[0]] for rat in rubric.get_rating_fields()},
                "comment": {com[1]: data[com[0]] for com in rubric.get_comment_fields()}
            }

            sr.set_data(ratings)
            sr.save()

        return redirect('index')
    elif request.method == 'GET':
        data = request.GET

        if 'action' not in data: return HttpResponseBadRequest()

        if data['action'] == 'dismissmusic':
            ms = MusicSuggestion(
                student=request.user.student,
                song='NULL',
                for_playlist=False,
                is_null=True
            )

            ms.save()
        elif data['action'] == 'approvespeechrating':
            evl = SpeechRating.objects.get(id=data['id'])
            evl.available_to_view = True

            evl.save()
        elif data['action'] == 'music_search':
            results = search(request, f"{data['song_name']} {data['song_artist']}")

            print(results)

            if results:
                return JsonResponse(results["tracks"]["items"][0])

        return redirect('index')
    return HttpResponseBadRequest()


def back_to_work(request):
    return render(request, 'app/backtowork.html')


def redirect_robotics(request):
    return redirect('https://docs.google.com/forms/d/e/1FAIpQLSd5rXYIFaysv2E4qnHkr0-0tdg35cLJU-u72qNp2EjqFjBIKA/viewform?usp=sf_link')
