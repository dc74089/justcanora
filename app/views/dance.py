from django.shortcuts import render


def dance_index(request):
    return render(request, 'app/dance/dance.html')