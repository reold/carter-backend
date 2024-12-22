from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from asyncio import Event, Queue
from uuid import uuid4 as uuid
import json
import time

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

run_status = Event()

app.add_event_handler("startup", lambda: run_status.set())
app.add_event_handler("shutdown", lambda: run_status.clear())

rooms = {}
clients = {}


@app.get("/")
def root():
    return "Welcome to Carter's Backend server!"


@app.get("/room/new")
async def new_room(id: str, username: str, room_name: str):
    room_id = uuid().hex
    rooms[room_id] = {"owner": id, "clients": [id], "room_name": room_name}
    clients[id] = {"messages": Queue(), "username": username}

    return {"success": True, "room_id": room_id}


@app.get("/room/join")
async def join_room(id: str, room_id: str, username: str):
    if not rooms.get(room_id):
        return {"success": False, "fault": "room doesn't exist"}

    rooms[room_id]["clients"].append(id)
    clients[id] = {"messages": Queue(), "username": username}

    return {"success": True, "room_name": rooms[room_id]["room_name"]}


@app.get("/room/info")
async def info_room(room_id: str):
    if not rooms.get(room_id):
        return {"success": False, "fault": "room doesn't exist"}

    return {"success": True, "room_name": rooms[room_id]["room_name"]}


@app.get("/room/listen")
async def listen_room(id: str):

    if not clients.get(id):
        return {"success": False, "fault": "client doesn't exist"}

    await clients[id]["messages"].put(
        '{"type": "conn", "info": "connection successfull"}'
    )

    async def make_content():
        while run_status.is_set():
            msg = await clients[id]["messages"].get()
            yield f"data: {msg}\n\n"

    return StreamingResponse(make_content(), media_type="text/event-stream")


@app.get("/room/broadcast")
async def broadcast_room(id: str, room_id: str, msg: str = "Hello, world!"):
    if not clients.get(id):
        return {"success": False, "fault": "client doesn't exist"}
    if not rooms.get(room_id):
        return {"success": False, "fault": "room doesn't exist"}

    sender = clients.get(id)

    for client_id in rooms[room_id]["clients"]:
        if clients.get(client_id):
            await clients[client_id]["messages"].put(
                json.dumps(
                    {
                        "type": "msg",
                        "content": msg,
                        "username": sender["username"],
                        "id": id,
                        "time": str(time.time()),
                    }
                )
            )

    return {"success": True}


@app.get("/room/log")
async def log_room():

    return {"success": True, "rooms": rooms}
