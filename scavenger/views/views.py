import json
import random

from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from scavenger.models import Team, Hunt, Kiosk, Riddle


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
    try:
        t = Team.objects.get(id=request.session['team'])

        return render(request, 'scavenger/team.html', {
            'team': t,
            'final_answer': t.hunt.final_password
        })
    except:
        if 'team' in request.session:
            del request.session['team']

        return redirect('scavenger-create-team')


@csrf_exempt
def get_team_state(request):
    if request.method == "GET":
        if 'team' in request.session:
            t = Team.objects.get(id=request.session['team'])
            return JsonResponse(t.get_state())
        else:
            return HttpResponseBadRequest()
    elif request.method == "POST":
        if 'action' in request.POST:
            if request.POST['action'] == 'dismiss_popup':
                t = Team.objects.get(id=request.session['team'])
                t.acknowledge_popup()

                return HttpResponse(status=200)


@csrf_exempt
def answer_question(request):
    if request.method == "POST":
        team = Team.objects.get(id=request.session['team'])
        q = Riddle.objects.get(id=team.get_state().get("riddle"))

        team.destination.set_state_qr()

        ans = request.POST['answer']

        if ans.strip().lower() == q.answer.strip().lower():
            team.final_password_progression += 1
            team.solved.add(q)
            team.save()

            if team.final_password_progression >= len(team.hunt.final_password):
                team.set_state_message("You've got all the letters! Head back to the classroom.")
                return JsonResponse({
                    "result": True,
                })

            kiosks = Kiosk.objects.filter(active=True).exclude(id=team.destination.id)

            occupied_kiosk_ids = [t.destination.id for t in Team.objects.all()]
            empty_kiosks = [k for k in kiosks if k not in occupied_kiosk_ids]

            if empty_kiosks:
                k = random.choice(list(empty_kiosks))
            else:
                k = random.choice(list(kiosks))

            team.set_new_destination(k)

            return JsonResponse({
                "result": True
            })
        else:
            kiosks = Kiosk.objects.filter(active=True).exclude(id=team.destination.id)

            k = random.choice(list(kiosks))

            team.set_new_destination(k)

            return JsonResponse({
                "result": False
            })


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

            if team.destination.id == kiosk.id:
                rq = Riddle.objects.all().difference(team.solved.all())

                print(rq, team.solved.all())

                if rq.exists():
                    riddle = random.choice(list(rq))
                else:
                    return

                team.set_state_riddle(riddle.id)
                kiosk.set_state_message(riddle.question)
                kiosk.set_current_team(team.name)

                return JsonResponse({
                    "team_name": team.name
                })
            else:
                return JsonResponse({
                    "error": f"You're in the wrong place! Go to the {team.destination.location}"
                })
