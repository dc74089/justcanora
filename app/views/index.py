from django.http import HttpResponse
from django.shortcuts import render, redirect

from app.cardproviders.allcards import allcards
from app.models import HelpRequest
from app.spotify import spotify, playlists


def index(request):
    if request.user.is_authenticated:
        cards = allcards(request)

        return render(request, "app/index.html", {
            'cards': cards
        })

    return redirect('login')


def tv(request):
    return render(request, "app/tv.html", {
        "helprequests": HelpRequest.objects.filter(satisfied=False).order_by('timestamp'),
    })


def dev(request):
    if spotify.session_needs_login(request):
        request.session['next'] = 'dev'
        request.session.save()

        return redirect(spotify.get_session_login_url(request))
    else:
        playlists.create_playlist(request, "Test Playlist")
        return HttpResponse(status=200)
