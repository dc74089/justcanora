from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from scavenger.models import Kiosk, Team


def admin(request):
    return render(request, 'scavenger/admin.html')


@staff_member_required
@csrf_exempt
def do_action(request):
    if request.method == "POST" and 'action' in request.POST:
        action = request.POST['action']

        if action == "start":
            for kiosk in Kiosk.objects.all():
                kiosk.set_state_qr()

            kiosks = Kiosk.objects.all()
            i = 0

            for team in Team.objects.all():
                team.set_new_destination(kiosks[i])
                i += 1
                i %= len(kiosks)

            return HttpResponse("Game Started.")

        elif action == "message":
            for kiosk in Kiosk.objects.all():
                kiosk.set_state_message(request.POST.get('message', request.POST.get("data", "Return to the classroom")))

            for team in Team.objects.all():
                team.set_state_message(request.POST.get('message', request.POST.get("data", "Return to the classroom")))

            return HttpResponse("Game Ended.")
