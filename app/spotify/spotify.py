import os

import spotipy
from spotipy import SpotifyOAuth, CacheHandler

from app.models import FeatureFlag


class DatabaseCacheHandler(CacheHandler):
    def get_cached_token(self):
        flag, _ = FeatureFlag.objects.get_or_create(id='fab_now_playing')
        return flag.get_config().get("token", "")

    def save_token_to_cache(self, token_info):
        print("Saving token")
        flag, _ = FeatureFlag.objects.get_or_create(id='fab_now_playing')
        flag.write_config({"token": token_info})
        flag.save()


def get_auth_manager(request):
    cache_handler = DatabaseCacheHandler()
    auth_manager = SpotifyOAuth(client_id="d4bcb66ee64e488fb946e743a66efa1d",
                                client_secret=os.getenv("SPOTIFY_SECRET"),
                                redirect_uri=f"{request.scheme}://{request.get_host()}/auth/spotify",
                                scope="user-read-currently-playing,playlist-read-private,playlist-read-collaborative,playlist-modify-private,playlist-modify-public,streaming",
                                cache_handler=cache_handler,
                                show_dialog=True)

    return auth_manager


def get_default_auth_manager():
    cache_handler = DatabaseCacheHandler()
    auth_manager = SpotifyOAuth(client_id="d4bcb66ee64e488fb946e743a66efa1d",
                                client_secret=os.getenv("SPOTIFY_SECRET"),
                                redirect_uri=f"https://canorasclass.com/auth/spotify",
                                scope="user-read-currently-playing,playlist-read-private,playlist-read-collaborative,playlist-modify-private,playlist-modify-public,streaming",
                                cache_handler=cache_handler,
                                show_dialog=True)

    return auth_manager


def get_spotify(request):
    if request is None:
        return spotipy.Spotify(auth_manager=get_default_auth_manager())

    return spotipy.Spotify(auth_manager=get_auth_manager(request))


def needs_login(request):
    am = get_auth_manager(request)

    return not am.validate_token(am.get_cached_token())


def get_login_url(request):
    request.session['spotify_auth'] = "database"
    request.session.save()

    am = get_auth_manager(request)

    return am.get_authorize_url()


def get_nowplaying(request):
    pass
