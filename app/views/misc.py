from django.http import HttpResponseBadRequest
from django.shortcuts import redirect

from app.models import MusicSuggestion, News


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
                for_playlist=data['song_type'] == 'class'
            )

            ms.save()

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
        elif data['action'] == 'dismissnews':
            n = News(
                student=request.user.student,
                is_null=True
            )

            n.save()

        return redirect('index')
