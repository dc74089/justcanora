from django.shortcuts import render, redirect

from app.cardproviders.allcards import allcards
from app.spotify import spotify


def index(request):
    if request.user.is_authenticated:
        cards = allcards(request)

        return render(request, "app/index.html", {
            'cards': cards
        })

    return redirect('login')


def dev(request):
    if spotify.needs_login(request):
        request.session['next'] = 'dev'
        request.session.save()

        return redirect(spotify.get_login_url(request))
    else:
        print(spotify.get_spotify(request).current_user_playlists())
