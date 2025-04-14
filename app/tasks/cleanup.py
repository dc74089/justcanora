from oauth2_provider.models import clear_expired

from app.models import MusicSuggestion, Course
from app.spotify import playlists


def cleanup_null():
    MusicSuggestion.objects.filter(is_null=True).delete()


def cleanup_playlists():
    for course in Course.objects.all():
        print(course)
        if course.playlist_id:
            songs = playlists.get_all_songs(None, course.playlist_id)

            for song in songs:
                reqs = MusicSuggestion.objects.filter(spotify_uri=song['track']['uri'], student__courses=course)

                if reqs.exists():
                    keep = False

                    for req in reqs:
                        if not req.is_expired():
                            keep = True

                    if not keep:
                        playlists.remove_song_from_playlist(None, course.playlist_id, song['track']['uri'])


def clear_tokens():
    clear_expired()
