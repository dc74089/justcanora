import random

from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect

from .models import Team, Hunt, Kiosk


def create_team(request):
    if 'team' in request.session:
        return redirect('scavenger-team-home')

    if request.method == 'POST':
        hunt = Hunt.objects.first()

        pw = list(hunt.final_password)
        random.shuffle(pw)
        pw = ''.join(pw)

        team = Team(
            hunt=hunt,
            name=request.POST['teamname'],
            final_password_order=pw
        )

        team.save()

        request.session['team'] = team.id
        request.session.save()

        return redirect('scavenger-team-home')
    else:
        return render(request, 'scavenger/index.html')


def join_team(request):
    if request.method == "GET" and 'team' in request.GET:
        request.session['team'] = request.GET['team']
        request.session.save()

        return redirect('scavenger-team-home')


def team_home(request):
    t = Team.objects.get(id=request.session['team'])

    return render(request, 'scavenger/team.html', {'team': t})


def get_team_state(request):
    if 'team' in request.session:
        pass
    else:
        return HttpResponseBadRequest()


def kiosk(request):
    if request.method == "POST":
        if 'location' in request.POST:
            k, _ = Kiosk.objects.get_or_create(
                hunt=Hunt.objects.first(),
                location=request.POST['location']
            )

            request.session['kiosk'] = k.id
            request.session.save()

            return redirect('scavenger-kiosk')
    else:
        if 'kiosk' in request.session:
            return render(request, 'scavenger/kiosk.html')
        else:
            return render(request, 'scavenger/kiosk_setup.html')


def kiosk_state(request):
    pass
