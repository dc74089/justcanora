from django.template.loader import render_to_string

from app.models import FeatureFlag, HelpRequest


def allcards(request):
    return [x for x in [help_request(request)] if x is not None]

def help_request(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_help')

    if enabled:
        student = request.user.student

        if HelpRequest.objects.filter(student=student).filter(satisfied=False).exists():
            return render_to_string('app/cards/help_existingrequest.html', request=request)
        else:
            return render_to_string('app/cards/help_newrequest.html', request=request)

    return None
