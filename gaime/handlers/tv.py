from asgiref.sync import sync_to_async
from django.db.models import Avg
from django.template.loader import render_to_string

from justcanora import sio

sio = sio.sio


@sync_to_async(thread_sensitive=True)
def _get_game():
    from gaime.models import Game
    return Game.objects.prefetch_related('question').first()


@sync_to_async(thread_sensitive=True)
def _get_leaderboard():
    from gaime.models import Player, Game, groups

    g = Game.objects.first()

    if g.teams:
        teams = (x[0] for x in groups)

        out = []

        for team in teams:
            team_players = Player.objects.filter(group=team)

            score_avg = team_players.aggregate(avg=Avg('points'))['avg']
            disp = team_players.first().get_group_display()

            out.append((disp, score_avg))

        out.sort(key=lambda x: x[1], reverse=True)

        return render_to_string('gaime/screen_tv_leaderboard.html', {
            "rows": out
        })
    else:
        return render_to_string('gaime/screen_tv_leaderboard.html', {
            "rows": ((x.first_name(), x.points) for x in Player.objects.all().order_by('-points')[:5])
        })


def _question_html(q):
    if q.media_type == "image":
        return render_to_string('gaime/screen_tv_question_image.html', {
            "question": q
        })
    elif q.media_type == "text":
        return render_to_string('gaime/screen_tv_question_text.html', {
            "question": q
        })
    else:
        return "There was an error loading the question."


@sio.event
async def init_tv(sid):
    print(f"Init tv: {sid}")
    await sio.enter_room(sid, "tv")

    g = await _get_game()

    if g.state == "title":
        html = render_to_string('gaime/screen_tv_title.html')
    elif g.state == "instructions":
        html = render_to_string('gaime/screen_tv_instructions.html')
    elif g.state == "question" or g.state == "review":
        q = g.question

        html = _question_html(q)
    elif g.state == "scores":
        html = await _get_leaderboard()
    else:
        html = "Illegal State"


    await sio.emit("screen", {
        "section": g.state,
        "html": html
    }, to=sid)


async def title_card():
    await sio.emit("screen", {
        "section": "title",
        "html": render_to_string('gaime/screen_tv_title.html')
    })


async def intro():
    from gaime.tools import ai, scripts

    await ai.send_speech(scripts.intro)


async def start_instructions():
    from gaime.tools import ai, scripts

    await ai.send_speech(scripts.instructions)

    await sio.emit("screen", {
        "section": "instructions",
        "html": render_to_string('gaime/screen_tv_instructions.html')
    })


async def question(q):
    from gaime.tools import ai, scripts

    qhtml = _question_html(q)

    await ai.send_speech(scripts.question_intro())

    await sio.emit("screen", {
        "section": "question",
        "html": qhtml
    })


async def answer():
    g = await _get_game()
    q = g.question

    qhtml = _question_html(q)

    await sio.emit("screen", {
        "section": "answer",
        "html": qhtml
    })


async def scores():
    from gaime.tools import ai

    board = await _get_leaderboard()
    await ai.speak_summarize_leaderboard(board)

    await sio.emit("screen", {
        "section": "scores",
        "html": board
    })


async def results():
    pass
