from asgiref.sync import sync_to_async
from django.template.loader import render_to_string

from gaime.models import groups
from justcanora import sio

sio = sio.sio


@sync_to_async(thread_sensitive=True)
def _get_leaderboard():
    from gaime.models import Player, Game

    g = Game.objects.first()

    if g.teams:
        teams = (x[0] for x in groups)

        out = []

        for team in teams:
            team_players = Player.objects.filter(group=team)

            score_avg = team_players.aggregate(avg=groups.Avg('score'))['avg']

            out.append((team, score_avg))

        out.sort(key=lambda x: x[1], reverse=True)

        return render_to_string('gaime/partial_tv_leaderboard.html', {
            "rows": out
        })
    else:
        return render_to_string('gaime/partial_tv_leaderboard.html', {
            "rows": (x.first_name(), x.points for x in Player.objects.all().order_by('-score')[:10])
        })


@sio.event
async def init_tv(sid):
    print(f"Init tv: {sid}")
    await sio.enter_room(sid, "tv")


async def title_card():
    await sio.emit("screen", {
        "section": "title"
    })


async def intro():
    from gaime.tools import ai, scripts

    await ai.send_speech(scripts.intro)


async def start_instructions():
    from gaime.tools import ai, scripts

    await sio.emit("screen", {
        "section": "instructions"
    })

    await ai.send_speech(scripts.instructions)


async def question():
    pass


async def answer():
    pass


async def scores():
    await sio.emit("screen", {
        "section": "scores",
        "board": await _get_leaderboard()
    })


async def results():
    pass
