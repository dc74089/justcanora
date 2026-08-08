from aitutor.utils.enrollment import tutor_languages


def context_processor(request):
    languages = []

    try:
        if request.user.is_authenticated:
            languages = tutor_languages(request.user.student)
    except Exception:
        pass

    return {
        # tutor_languages already accounts for the per-course flags, so this is
        # true only when the student has at least one course that is both theirs
        # and currently switched on.
        "tutor_available": len(languages) > 0,
    }
