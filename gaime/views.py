from django.http import HttpResponseBadRequest
from django.shortcuts import render

from gaime.models import Player


# Create your views here.
def index(request):
    return render(request, 'gaime/client.html')


def tv(request):
    return render(request, 'gaime/tv.html')


def admin(request):
    return render(request, 'gaime/admin.html')


def players(request):
    if request.method == "POST":
        if 'names' not in request.POST: return HttpResponseBadRequest()

        names = request.POST['names'].split('\n')

        Player.objects.all().delete()

        i = 0
        for name in names:
            last, first = name.split(',')
            last = last.strip()
            first = first.strip()

            p, created = Player.objects.get_or_create(name=f"{first} {last}")
            p.group = i % 4 + 1
            p.save()

            i += 1

    return render(request, 'gaime/players.html', {
        "players": Player.objects.all().order_by('group')
    })
