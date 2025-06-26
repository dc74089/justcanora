from app.models import FeatureFlag


def context_processor(request):
    ff, _ = FeatureFlag.objects.get_or_create(id="tutor_available")

    languages = []

    try:
        if request.user.is_authenticated:
            if 'APCSA' in request.user.student.courses.values_list('type', flat=True):
                languages.append("java")
            if 'CS2' in request.user.student.courses.values_list('type', flat=True):
                languages.append("python")
    except:
        pass

    return {
        "tutor_available": bool(ff) and len(languages) > 0,
    }