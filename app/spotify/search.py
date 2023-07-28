from django.http import JsonResponse

from app.spotify import spotify


def search(request):
    sp = spotify.get_spotify(request)

    q = request.GET['q']

    results = sp.search(q, market='US', limit=20, type='track')
    return JsonResponse(results)
