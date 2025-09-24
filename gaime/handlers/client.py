from asgiref.sync import sync_to_async
from django.template.loader import render_to_string

from justcanora import sio

sio = sio.sio


@sync_to_async(thread_sensitive=True)
def _get_game():
    from gaime.models import Game
    return Game.objects.prefetch_related('question').first()


@sync_to_async(thread_sensitive=True)
def _build_player_select():
    from gaime.models import Player, groups
    return render_to_string('gaime/screen_player_select.html', {
        "players": Player.objects.all().order_by('name')
    })


@sync_to_async(thread_sensitive=True)
def _build_team_reveal(pid):
    from gaime.models import Player
    player = Player.objects.get(id=pid)

    return render_to_string('gaime/screen_player_teamname.html', {
        "player": player
    })


@sync_to_async(thread_sensitive=True)
def _add_to_score(pid, amount):
    from gaime.models import Player

    player = Player.objects.get(id=pid)
    player.points += amount
    player.save()


@sio.event
async def init_player(sid, data={}):
    print(f"Init Player: {sid}", data)
    await sio.enter_room(sid, "player")

    if 'player_id' in data:
        await select_player(sid, {
            "player_id": data['player_id']
        })
    else:
        await send_player_select(sid)


async def send_player_select(sid):
    await sio.emit("client", {
        "section": "select",
        "html": await _build_player_select()
    }, to=sid)


@sio.event
async def select_player(sid, data):
    print("SID is", sid, "PID is", data.get('player_id'))

    pid = data.get('player_id')
    await sio.enter_room(sid, "player" + data.get('player_id'))

    await wait(sid)


async def wait(to='player'):
    await sio.emit("client", {
        "section": "wait",
        "html": render_to_string('gaime/screen_player_wait.html')
    }, to=to)


async def team_name(to='player'):
    await sio.emit("teamtrigger", to=to)


@sio.event
async def get_team(sid, data):
    print(f"Team tickle: {sid}, {data}")
    await sio.emit("client", {
        "section": "team",
        "html": await _build_team_reveal(data.get('player_id'))
    }, to=sid)


async def question():
    await sio.emit("client", {
        "section": "question",
        "html": render_to_string('gaime/screen_player_question.html')
    })


@sio.event
async def answer(sid, data):
    from gaime.handlers import admin
    print(f"Answer: {sid}, {data}")

    g = await _get_game()
    await wait(sid)

    if bool(data.get('answer')) == g.question.is_ai:
        await _add_to_score(data.get('player_id'), 1)

    await admin.send_player_table()
