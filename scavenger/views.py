import random

from django.shortcuts import render

from .models import Team, Hunt


def create_team(request):
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
    else:
        return render(request, 'scavenger/index.html')
