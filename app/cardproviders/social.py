from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from app.models import News, FeatureFlag


def allcards(request):
    return [x for x in [submit_news(request)] if x is not None]


def submit_news(request):
    enabled, _ = FeatureFlag.objects.get_or_create(id='card_news_submit')
    if not enabled: return None

    if timezone.now().astimezone(settings.EST).date().weekday() in settings.NEWS_DAYS:
        nq = News.objects.filter(student=request.user.student).order_by('-added')

        if not nq or timezone.now() - nq.first().added > timezone.timedelta(hours=18):
            return render_to_string('app/cards/news.html', request=request)
