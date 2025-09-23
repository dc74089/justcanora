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

@sio.event
async def init_player(sid):
    print(f"Init Player: {sid}")
    await send_player_select(sid)


async def send_player_select(sid):
    await sio.emit("client", {
        "section": "select",
        "html": await _build_player_select()
    }, to=sid)


@sio.event
async def select_player(sid, data):
    print("SID is", type(sid))
    # TODO: Save SID-player mapping somehow