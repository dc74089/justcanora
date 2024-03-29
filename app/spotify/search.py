from pprint import pprint

from app.spotify import spotify


def search(request, q, filter_explicit=True):
    sp = spotify.get_spotify(request)

    results = sp.search(q, market='US', limit=20, type='track')

    if filter_explicit:
        results = dict(results)

        results['tracks']['items'] = [s for s in results['tracks']['items'] if not s['explicit']]

    return results


def get_by_uri(request, uri):
    sp = spotify.get_spotify(request)

    print("Getting Track!")
    
    return sp.track(uri)
