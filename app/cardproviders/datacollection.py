from django.template.loader import render_to_string

from app.models import DataCollectionQuestion, Student, FeatureFlag


def allcards(request):
    return [x for x in dataquestions(request) if x is not None]


def dataquestions(request):
    flag, _ = FeatureFlag.objects.get_or_create(id="card_data_collection")
    if not flag: return []

    s: Student = request.user.student
    qq = DataCollectionQuestion.objects.filter(courses__in=s.courses.all(), is_open=True).exclude(answers__student=s)

    return [
        render_to_string(
            "app/cards/datacollection.html",
            {"q": q},
            request
        )
        for q in qq]
