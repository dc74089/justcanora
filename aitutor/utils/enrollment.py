"""Which tutor languages a student may use right now.

Access is the intersection of two things: the courses a student is enrolled in,
and the per-course feature flags that say the tutor is currently switched on for
that course. Single source of truth for both, because the nav link, the agent
picker, new-conversation validation, and the send endpoint all have to agree —
if they disagree, a student is either shown an agent they can't use or blocked
from one they should have.
"""

from app.models import FeatureFlag

# Ordered so callers get a stable, predictable language list.
COURSE_TYPE_TO_LANGUAGE = {
    "APCSA": "java",
    "CS2": "python",
    "CS1": "html",
}

# Per-course kill switches, flipped from the staff admin page. A course with its
# flag off behaves as though the student weren't enrolled in it at all.
COURSE_TYPE_TO_FLAG = {
    "APCSA": "tutor_available_apcsa",
    "CS2": "tutor_available_cs2",
    "CS1": "tutor_available_cs1",
}

FLAG_LABELS = {
    "tutor_available_apcsa": "AI Tutor — AP CSA (Java)",
    "tutor_available_cs2": "AI Tutor — CS2 (Python)",
    "tutor_available_cs1": "AI Tutor — Web Dev (HTML/CSS)",
}


def enabled_course_types():
    """Course types whose tutor flag is currently on."""
    enabled_flags = set(
        FeatureFlag.objects
        .filter(id__in=COURSE_TYPE_TO_FLAG.values(), enabled=True)
        .values_list("id", flat=True)
    )
    return {course_type for course_type, flag in COURSE_TYPE_TO_FLAG.items() if flag in enabled_flags}


def tutor_languages(student):
    """Agent languages this student may use right now, e.g. ``["java", "python"]``.

    Empty when they're enrolled in none of the tutor courses, or when every
    course they are in has had its flag switched off.
    """
    enrolled = set(student.courses.values_list("type", flat=True))
    available = enrolled & enabled_course_types()
    return [lang for course_type, lang in COURSE_TYPE_TO_LANGUAGE.items() if course_type in available]
