import os

import spotipy
from spotipy import SpotifyOAuth, CacheHandler
from spotipy.oauth2 import SpotifyOauthError

from app.models import FeatureFlag

# One scope string shared by every auth manager. The browser flow and the
# background/cron flow read the same cached token, so they must request the
# same scopes — otherwise spotipy's scope-subset check rejects the token and
# forces a needless re-authorize.
SCOPE = ("user-modify-playback-state,user-read-playback-state,user-read-currently-playing,"
         "playlist-read-private,playlist-read-collaborative,playlist-modify-private,"
         "playlist-modify-public,streaming")


class DatabaseCacheHandler(CacheHandler):
    def get_cached_token(self):
        flag, _ = FeatureFlag.objects.get_or_create(id='fab_now_playing')
        return flag.get_config().get("token", "")

    def save_token_to_cache(self, token_info):
        # Spotify sometimes omits `scope` on a refresh response, and spotipy's
        # SpotifyOAuth does not re-attach it. Without a scope, validate_token()
        # rejects an otherwise-valid token and forces a re-authorize. Backfill
        # it so a good refresh token keeps working across days.
        if isinstance(token_info, dict) and not token_info.get("scope"):
            token_info["scope"] = SCOPE

        flag, _ = FeatureFlag.objects.get_or_create(id='fab_now_playing')
        flag.write_config({"token": token_info})
        flag.save()


def get_auth_manager(request):
    cache_handler = DatabaseCacheHandler()
    auth_manager = SpotifyOAuth(client_id="d4bcb66ee64e488fb946e743a66efa1d",
                                client_secret=os.getenv("SPOTIFY_SECRET"),
                                redirect_uri=f"{request.scheme}://{request.get_host()}/auth/spotify",
                                scope=SCOPE,
                                cache_handler=cache_handler,
                                show_dialog=False)

    return auth_manager


def get_default_auth_manager():
    cache_handler = DatabaseCacheHandler()
    auth_manager = SpotifyOAuth(client_id="d4bcb66ee64e488fb946e743a66efa1d",
                                client_secret=os.getenv("SPOTIFY_SECRET"),
                                redirect_uri=f"https://tr.canora.us/auth/spotify",
                                scope=SCOPE,
                                cache_handler=cache_handler,
                                show_dialog=False)

    return auth_manager


def get_spotify(request):
    if request is None:
        return spotipy.Spotify(auth_manager=get_default_auth_manager())

    return spotipy.Spotify(auth_manager=get_auth_manager(request))


def needs_login(request):
    # We're logged in as long as we hold a usable refresh token. Key off that
    # (not spotipy's scope-gated validate_token, which rejects a good token when
    # its cached scope drifts) so a valid refresh token keeps us authenticated
    # across days. Only prompt to re-authorize when there's no refresh token or
    # the refresh actually fails.
    try:
        am = get_auth_manager(request)
        token_info = am.cache_handler.get_cached_token()

        if not token_info or not token_info.get("refresh_token"):
            return True

        if "expires_at" not in token_info or am.is_token_expired(token_info):
            am.refresh_access_token(token_info["refresh_token"])

        return False
    except SpotifyOauthError:
        return True


def get_login_url(request):
    request.session['spotify_auth'] = "database"
    request.session.save()

    am = get_auth_manager(request)

    return am.get_authorize_url()


def get_nowplaying(request):
    pass
