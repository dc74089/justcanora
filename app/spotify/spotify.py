import os

import spotipy
from spotipy import SpotifyOAuth, DjangoSessionCacheHandler


def get_auth_manager(request):
    cache_handler = DjangoSessionCacheHandler(request)
    auth_manager = SpotifyOAuth(client_id="d4bcb66ee64e488fb946e743a66efa1d",
                                client_secret=os.getenv("SPOTIFY_SECRET"),
                                redirect_uri=f"{request.scheme}://{request.get_host()}/auth/spotify",
                                scope="user-read-currently-playing,playlist-read-private,playlist-read-collaborative,playlist-modify-private,playlist-modify-public",
                                cache_handler=cache_handler,
                                show_dialog=True)

    return auth_manager


def get_spotify(request):
    return spotipy.Spotify(auth_manager=get_auth_manager(request))


def needs_login(request):
    am = get_auth_manager(request)

    return not am.validate_token(am.get_cached_token())


def get_login_url(request):
    am = get_auth_manager(request)

    return am.get_authorize_url()
