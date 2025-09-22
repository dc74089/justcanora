from asgiref.sync import sync_to_async
from django.template.loader import render_to_string

from justcanora import sio

sio = sio.sio


@sync_to_async(thread_sensitive=True)
def _get_players_table():
    from gaime.models import Player

    return render_to_string('gaime/partial_admin_players_table.html', {
        'players': Player.objects.all().order_by('group')
    })


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


async def send_player_table(to='admin'):
    await sio.emit("players_list", {
        "html": await _get_players_table()
    }, room=to)


@sio.event
async def change_score(sid, data):
    print(f"Change score: {sid}, {data}")
    await _add_to_score(data['pid'], data['amount'])
    await send_player_table()


@sio.event
async def title(sid):
    from gaime.handlers import tv

    await tv.title_card()


@sio.event
async def intro(sid):
    from gaime.handlers import tv

    await _set_groups(True)
    await tv.intro()


@sio.event
async def instructions(sid):
    from gaime.handlers import tv

    await _set_groups(True)
    await tv.start_instructions()