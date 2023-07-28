from django.shortcuts import render, redirect

from app.cardproviders.allcards import allcards


def index(request):
    if request.user.is_authenticated:
        cards = allcards(request)

        return render(request, "common/index.html", {
            'cards': cards
        })

    return redirect('login')


def dev(request):
    return render(request, 'common/error.html', {
        "short": "I can't find that",
        "message": "Here's some text"
    })
