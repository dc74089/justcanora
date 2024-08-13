from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render


def setup_instructions(request):
    return render(request, 'app/python/jetbrains-fls.html')


@login_required
def userdata(request):
    if request.user.is_authenticated:
        stu = request.user.student

        return JsonResponse({
            "id": stu.id,
            "email": stu.email,
            "name": stu.full_name(),
            "verification_state": True,
            "groups": ["students"],
            "avatar": stu.picture.url if stu.picture else None,
        })
    else:
        return HttpResponseForbidden()