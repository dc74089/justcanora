from asgiref.sync import sync_to_async
from django.template.loader import render_to_string

from justcanora import sio

sio = sio.sio

@sio.event
async def init_client(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit("server_message", {"msg": "Welcome!"}, to=sid)