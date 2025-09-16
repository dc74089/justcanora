from justcanora import sio

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