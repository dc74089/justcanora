from django.shortcuts import render


def index(request):
    return render(request, "common/index.html")


def dev(request):
    return render(request, 'common/error.html', {
        "short": "I can't find that",
        "message": "Here's some text"
    })