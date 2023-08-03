from pprint import pprint

from app.spotify import spotify


def create_playlist(request, name):
    sf = spotify.get_spotify(request)

    user = sf.current_user()
    pl = sf.user_playlist_create(user['id'], name)

    return pl['uri']


def add_song_to_playlist(request, playlist, song_uri, allow_duplicates=False):
    sf = spotify.get_spotify(request)

    if not allow_duplicates:
        pl = sf.playlist_items(playlist, limit=50)
        tracks = [item['track'] for item in pl['items']]

        if pl['total'] > 50:
            for i in range(50, pl['total'], 50):
                pl = sf.playlist_items(playlist, limit=50, offset=i)
                tracks.extend([item['track'] for item in pl['items']])

        uris = [track['uri'] for track in tracks]
        if song_uri in uris: return

    sf.playlist_add_items(playlist, [song_uri])
