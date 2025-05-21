from app.models import FeatureFlag


def context_processor(request):
    ff, _ = FeatureFlag.objects.get_or_create(id="tutor_available")

    return {
        "tutor_available": bool(ff)
    }