from django.shortcuts import render


def index(request):
    return render(request, "app/curriculum_night/cn.html", {
        "qr": "qr" in request.GET
    })


def big_qr(request):
    return render(request, "app/curriculum_night/bigqr.html", {
        "qr": True
    })
