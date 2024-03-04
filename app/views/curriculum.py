from django.shortcuts import render


def index(request):
    return render(request, "app/curriculum_night/2024.html")


def index_dark(request):
    return render(request, "app/curriculum_night/2024-darkmode.html")
