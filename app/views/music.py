from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from app.models import Course, MusicSuggestion
from app.spotify import spotify
from app.spotify.search import search


@staff_member_required
def music_queue(request):
    if spotify.needs_login(request):
        request.session['next'] = 'music_queue'
        request.session.save()

        return redirect(spotify.get_login_url(request))

    return render(request, 'app/admin/music_queue.html', {
        "courses": Course.objects.all().order_by('semester', 'period'),
        "suggestions": {
            course.id: MusicSuggestion.objects.filter(student__courses=course) for course in Course.objects.all()
        }
    })


def search_table(request):
    q = request.GET.get('q')

    if not q: return HttpResponseBadRequest()

    results = search(request, q)

    return render(request, 'app/admin/music_partial_table.html', {
        'songs': results['tracks']['items']
    })
