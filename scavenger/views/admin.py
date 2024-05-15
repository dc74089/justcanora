from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from scavenger.models import Kiosk, Team, Hunt


@staff_member_required
def admin(request):
    return render(request, 'scavenger/admin.html', {
        "teams": Team.objects.all(),
        "kiosks": Kiosk.objects.all(),
    })


@staff_member_required
def table(request):
    hunt = Hunt.objects.first()

    return render(request, 'scavenger/admin-table.html', {
        "teams": Team.objects.all(),
        "kiosks": Kiosk.objects.all(),
        "final_password_letters": len(hunt.final_password)
    })


@staff_member_required
@csrf_exempt
def do_action(request):
    if request.method == "POST" and 'action' in request.POST:
        action = request.POST['action']

        if action == "start":
            for kiosk in Kiosk.objects.filter(active=True):
                kiosk.set_state_qr()

            kiosks = Kiosk.objects.filter(active=True)
            i = 0

            for team in Team.objects.all():
                team.set_new_destination(kiosks[i])
                i += 1
                i %= len(kiosks)

            return HttpResponse("Game Started.")
        elif action == "popup":
            for team in Team.objects.all():
                team.send_popup(request.POST['data'])

            return HttpResponse("Sent.")
        elif action == "message":
            for kiosk in Kiosk.objects.all():
                kiosk.set_state_message(
                    request.POST.get('message', request.POST.get("data", "Return to the classroom")))

            for team in Team.objects.all():
                team.set_state_message(request.POST.get('message', request.POST.get("data", "Return to the classroom")))

            return HttpResponse("Game Frozen by Message.")
        elif action == "kiosk_init":
            kiosk = Kiosk.objects.get(id=request.POST['data'])

            kiosk.set_state_qr()
            return HttpResponse("Kiosk Initialized.")
        elif action == "team_init":
            team = Team.objects.get(id=request.POST['data'])

            team.set_new_destination(Kiosk.objects.filter(active=True).order_by('?').first())
            team.set_state_qr()

            return HttpResponse("Team Initialized.")
        elif action == "team_to_final":
            team = Team.objects.get(id=request.POST['data'])

            if team.final_password_progression >= len(team.hunt.final_password):
                team.set_state_final()
                return HttpResponse("Set team to final screen.")
            else:
                return HttpResponse("ERROR: Team doesn't have all letters. Didn't touch them.")
