from asgiref.sync import sync_to_async
from django.template.loader import render_to_string

from justcanora import sio

from gaime.handlers import client, tv, admin  # needed to register handlers

client
tv
admin

sio = sio.sio


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit("server_message", {"msg": "Welcome!"}, to=sid)


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")


@sio.event
async def ping(sid, data):
    print(f"Got ping from {sid}: {data}")
    await sio.emit("pong", {"echo": data}, to=sid)


@sio.event
async def dev(sid):
    print(f"Dev: {sid}")

    from gaime.tools import ai

    await ai.send_speech("This is a developer test.")
