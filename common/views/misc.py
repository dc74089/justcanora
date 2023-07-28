from django.http import HttpResponseBadRequest
from django.shortcuts import redirect


def misc_action(request):
    if request.method == 'POST':
        data = request.POST

        if 'action' not in data: return HttpResponseBadRequest()

        if data['action'] == 'setgrade':
            s = request.user.student
            s.grade = int(data['grade'])
            s.save()
        elif data['action'] == 'setbday':
            s = request.user.student
            s.bday = data['bday']
            s.save()

        return redirect('index')