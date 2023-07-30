from pprint import pprint

from django.http import JsonResponse

from app.spotify import spotify


def search(request, q, filter_explicit=True):
    sp = spotify.get_spotify(request)

    results = sp.search(q, market='US', limit=20, type='track')

    pprint(results)

    if filter_explicit:
        results = dict(results)

        results['tracks']['items'] = [s for s in results['tracks']['items'] if not s['explicit']]

    return results
