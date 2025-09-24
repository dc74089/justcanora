import asyncio

from asgiref.sync import sync_to_async
from django.template.loader import render_to_string

from justcanora import sio

sio = sio.sio


@sync_to_async(thread_sensitive=True)
def _get_game():
    from gaime.models import Game
    return Game.objects.prefetch_related('question').first()


@sync_to_async(thread_sensitive=True)
def _set_game_state(state, q=None):
    from gaime.models import Game
    game = Game.objects.first()
    game.state = state

    if q:
        game.question = q

    game.save()


@sync_to_async(thread_sensitive=True)
def _get_players_table():
    from gaime.models import Player

    return render_to_string('gaime/partial_admin_players_table.html', {
        'players': Player.objects.all().order_by('group')
    })


@sync_to_async(thread_sensitive=True)
def _get_questions():
    from gaime.models import Question

    return list(Question.objects.order_by('used', 'prompt'))


@sync_to_async(thread_sensitive=True)
def _get_question_by_id(qid):
    from gaime.models import Question
    return Question.objects.get(id=qid)


@sync_to_async(thread_sensitive=True)
def _mark_question_used(qid):
    from gaime.models import Question

    q = Question.objects.get(id=qid)
    q.used = True
    q.save()


@sync_to_async(thread_sensitive=True)
def _add_to_score(pid, amount):
    from gaime.models import Player

    player = Player.objects.get(id=pid)
    player.points += amount
    player.save()


@sync_to_async(thread_sensitive=True)
def _set_groups(groups_enabled):
    from gaime.models import Game
    game = Game.objects.first()
    game.teams = groups_enabled
    game.save()


@sio.event
async def init_admin(sid):
    print(f"Init admin: {sid}")
    await sio.enter_room(sid, "admin")

    await send_player_table(to=sid)


@sio.event
async def request_questions(sid):
    await send_questions_list(to=sid)


async def send_player_table(to='admin'):
    await sio.emit("players_list", {
        "html": await _get_players_table()
    }, room=to)


async def send_questions_list(to='admin'):
    qs = await _get_questions()

    html = render_to_string('gaime/partial_admin_question_select.html', {
        "questions": qs
    })

    await sio.emit("questions_list", {
        "questions": html
    }, room=to)


@sio.event
async def change_score(sid, data):
    print(f"Change score: {sid}, {data}")
    await _add_to_score(data['pid'], data['amount'])
    await send_player_table()


@sio.event
async def title(sid):
    from gaime.handlers import tv

    await _set_game_state("title")
    await tv.title_card()


@sio.event
async def intro(sid):
    from gaime.handlers import tv, client

    await _set_groups(True)
    await tv.intro()

    print("Intro delay")
    await asyncio.sleep(10)
    print("Intro delay done")

    await client.team_name()

@sio.event
async def instructions(sid):
    from gaime.handlers import tv, client

    await _set_game_state("instructions")
    await _set_groups(True)
    await client.wait()
    await tv.start_instructions()


@sio.event
async def question(sid, data):
    from gaime.handlers import tv

    q = await _get_question_by_id(data['qid'])
    await _mark_question_used(data['qid'])
    await _set_game_state("question", q)
    await tv.question(q)
    await client.question()
    await send_questions_list()


@sio.event
async def review(sid):
    from gaime.tools import ai, scripts
    from gaime.handlers import client

    g = await _get_game()

    script = scripts.yes() if g.question.is_ai else scripts.no()

    await _set_game_state("review")
    await client.wait()
    await ai.send_speech(script)


@sio.event
async def scores(sid):
    from gaime.handlers import tv, client

    await _set_game_state("scores")
    await client.wait()
    await tv.scores()


@sio.event
async def shatter_groups(sid):
    from gaime.handlers import tv, client

    await _set_groups(False)
    await client.wait()
    await tv.twist()
    await tv.scores()
