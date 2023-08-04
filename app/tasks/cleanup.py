from app.models import MusicSuggestion, News


def cleanup_null():
    MusicSuggestion.objects.filter(is_null=True).delete()
    News.objects.filter(is_null=True).delete()