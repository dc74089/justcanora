import json
import random

from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from .models import Team, Hunt, Kiosk, Riddle


def create_team(request):
    if 'team' in request.session:
        return redirect('scavenger-team-home')

    if request.method == 'POST':
        hunt = Hunt.objects.first()

        pw = list(hunt.final_password)
        random.shuffle(pw)
        pw = ''.join(pw)

        initial_state = {
            "state": "message",
            "message": "Waiting for the hunt to start"
        }

        team = Team(
            hunt=hunt,
            name=request.POST['teamname'],
            final_password_order=pw,
            state=json.dumps(initial_state)
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
        t = Team.objects.get(id=request.session['team'])
        return JsonResponse(t.get_state())
    else:
        return HttpResponseBadRequest()


@csrf_exempt
def answer_question(request):
    if request.method == "POST":
        team = Team.objects.get(id=request.session['team'])
        q = Riddle.objects.get(id=team.get_state().get("riddle"))

        ans = request.POST['answer']

        if ans.strip().lower() == q.answer.strip().lower():
            pass  #TODO: Pick up here


def kiosk(request):
    if request.method == "POST":
        if 'location' in request.POST:
            default_state = {
                "state": "message",
                "message": "Waiting for the hunt to start"
            }

            k, _ = Kiosk.objects.get_or_create(
                hunt=Hunt.objects.first(),
                location=request.POST['location'],
                state=json.dumps(default_state)
            )

            request.session['kiosk'] = k.id
            request.session.save()

            return redirect('scavenger-kiosk')
    else:
        if 'kiosk' in request.session:
            return render(request, 'scavenger/kiosk.html', {
                'kiosk': Kiosk.objects.get(id=request.session['kiosk'])
            })
        else:
            return render(request, 'scavenger/kiosk_setup.html')


@csrf_exempt
def kiosk_state(request):
    if request.method == "GET":
        if 'kiosk' in request.session:
            k = Kiosk.objects.get(id=request.session['kiosk'])
            return JsonResponse(k.get_state())
    elif request.method == "POST":
        data = request.POST

        if data['type'] == 'teamhere':
            team = Team.objects.get(id=data['team'])
            kiosk = Kiosk.objects.get(id=request.session['kiosk'])

            if team.get_state().get('destination') == kiosk.id:
                team_state = team.get_state()
                kiosk_state = kiosk.get_state()

                rq = Riddle.objects.all().difference(team.solved.all())

                print(rq, team.solved.all())

                if rq.exists():
                    riddle = random.choice(list(rq))
                else:
                    return

                team_state['state'] = "entry"
                team_state['riddle'] = riddle.id
                kiosk_state['state'] = "message"
                kiosk_state['message'] = riddle.question

                team.set_state(team_state)
                team.save()

                kiosk.set_state(kiosk_state)
                kiosk.save()

                return HttpResponse(status=200)
