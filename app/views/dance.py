import uuid

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from app.models import DanceRequestCategory, DanceRequest
from app.spotify.search import search


def dance_index(request):
    if request.user.is_authenticated:
        identity = request.user.email
    elif 'dance_request_identity' in request.session:
        identity = request.session['dance_request_identity']
    else:
        identity = str(uuid.uuid4())
        request.session['dance_request_identity'] = identity
        request.session.save()

    selected = {}
    for req in DanceRequest.objects.filter(requestor=identity):
        selected[req.category.id] = render_to_string("app/dance/partial_chosen_song.html", {
            "song": req.get_spotify_data(request)
        }, request)

    cats = []
    for cat in DanceRequestCategory.objects.all():
        if cat.id in selected:
            cat.selected = selected[cat.id]

        cats.append(cat)

    return render(request, 'app/dance/dance.html', {
        "categories": cats,
        "now_playing_available": False,
        "selected": selected,
    })


def dance_search(request):
    if request.method == 'GET' and 'q' in request.GET and 'category' in request.GET:
        results = search(request, request.GET['q'], filter_explicit=False, limit=5)

        return render(request, 'app/dance/partial_results_table.html', {
            'results': results['tracks']['items'],
            'category': request.GET['category']
        })


@csrf_exempt
def dance_choose(request):
    if request.method == 'POST' and 'category' in request.POST and 'song' in request.POST:
        if request.user.is_authenticated:
            identity = request.user.email
        elif 'dance_request_identity' in request.session:
            identity = request.session['dance_request_identity']
        else:
            identity = str(uuid.uuid4())
            request.session['dance_request_identity'] = identity
            request.session.save()


        q = DanceRequest.objects.filter(category=request.POST['category'], requestor=identity)
        if q.exists():
            q.delete()

        req = DanceRequest(
            requestor=identity,
            category_id=int(request.POST['category']),
            spotify_uri=request.POST['song'],
        )

        req.save()

        return render(request, 'app/dance/partial_chosen_song.html', {
            "song": req.get_spotify_data(request)
        })


def get_artist(data):
    try:
        return ", ".join(art['name'] for art in data['artists'])
    except:
        return ""


@login_required
def dance_view(request):
    reqs_by_uri = {}

    for req in DanceRequest.objects.all():
        if req.spotify_uri not in reqs_by_uri:
            reqs_by_uri[req.spotify_uri] = []

        reqs_by_uri[req.spotify_uri].append(req)


    out = []
    for uri, reqs in reqs_by_uri.items():
        out.append({
            "name": reqs[0].get_spotify_data(request).get('name'),
            "artist": get_artist(reqs[0].get_spotify_data(request)),
            "categories":  ",\n".join(set(req.category.name for req in reqs)),
            "popularity": reqs[0].get_spotify_data(request).get('popularity'),
            "count": len(reqs),
        })

    return render(request, 'app/dance/view_requests.html', {
        "requests": sorted(out, key=lambda x: x['count'], reverse=True),
    })
