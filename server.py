from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import random
from fastapi.websockets import WebSocket, WebSocketDisconnect
import json
from typing import Dict
import uuid
import numpy as np #replaceable for random.choice without replacement

NUM_BIANCHE = 3
NUM_NERE = 2
NUM_ROSSE = 2
NUM_BLU = 2
NUM_GIALLE = 1
NUM_TOTALE = NUM_BIANCHE + NUM_NERE + NUM_ROSSE + NUM_BLU + NUM_GIALLE

def profetizza():
    profezia = ['bianca'] * NUM_BIANCHE + ['nera'] * NUM_NERE + ['rossa'] * NUM_ROSSE + ['blu'] * NUM_BLU + ['gialla'] * NUM_GIALLE
    random.shuffle(profezia)
    return profezia[:3]

TURNO = None

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

BODYTYPES = ['tall','short','medium','large']
COLORS =  ['red','blue','green','yellow']
MISSIONS = ["A","B","C","D"]
PERSONALITY = ["Lord Fiddlebottom", "Colonel Bubble", "Madame Tsatsa", "Agent X"]
client_ids = []

associations = []

class Player:
    def __init__(self, bodytype = None, color=None, mission=None, personality=None, key=None):
        self.bodytype = bodytype
        self.color = color
        self.mission = mission
        self.personality = personality
        self.key = key
        self.client_id = None
        self.starting = False
        self.positions = []
    def setAttribute(self, color, body, mission, personality):
        self.color = color
        self.bodytype = body
        self.mission = mission
        self.personality = personality
        if color == 'red':
            self.positions = [2,27,31,52,*np.random.choice(BODYTYPES, size=4, replace=False)]
        elif color == 'green':
            self.positions = [14,24,35,55,*np.random.choice(BODYTYPES, size=4, replace=False)]
        elif color == 'blue':
            self.positions = [13,20,38,41,*np.random.choice(BODYTYPES, size=4, replace=False)]
        elif color == 'yellow':
            self.positions = [5,12,21,44,*np.random.choice(BODYTYPES, size=4, replace=False)]
        print("Position: ", self.positions)
    def toDict(self):
        return {
            "bodytype": self.bodytype,
            "color": self.color,
            "mission": self.mission,
            "personality": self.personality,
            "key": self.key,
            "id": self.client_id,
            "starting": self.starting,
            "positions": self.positions
        }

Player1 = Player()
Player2 = Player()
Player3 = Player()
Player4 = Player()
Players = [Player1, Player2, Player3, Player4]

def createNewPlayers():
    bodies = np.random.choice(BODYTYPES, size=4, replace=False)
    colors = np.random.choice(COLORS, size=4, replace=False)
    missions = np.random.choice(MISSIONS, size=4, replace=False)
    personalities = np.random.choice(PERSONALITY, size=4, replace=False)
    starting = random.randint(1,4)
    TURNO = starting
    print("Generated missions: ", missions)
    print("Generated bodies: ", bodies)
    print("Generated colors: ", colors)
    print("Generated personalities: ", personalities)
    print("Starting player: ", starting)
    if starting == 1:
        Player1.starting = True
    elif starting == 2:
        Player2.starting = True
    elif starting == 3:
        Player3.starting = True
    elif starting == 4:
        Player4.starting = True
    Player1.setAttribute(colors[0], bodies[0], missions[0], personalities[0])
    Player2.setAttribute(colors[1], bodies[1], missions[1], personalities[1])
    Player3.setAttribute(colors[2], bodies[2], missions[2], personalities[2])
    Player4.setAttribute(colors[3], bodies[3], missions[3], personalities[3])

createNewPlayers()

@app.get("/")
async def read_root():
    return HTMLResponse(open("index.html").read())

@app.post("/move_piece")
async def move_piece(request: Request, response: Response):
    body = await request.json()
    color = body["color"]
    bodytype = body["bodytype"]
    fromStep = body["fromStep"]
    toStep = body["toStep"]
    key = body["key"]
    actual_player = list(filter(lambda p: p.key == key, Players))[0]
    #if actual_player.key == key:

   

class ConnectionManager:
    def __init__(self):
        # client_id -> websocket
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_id = str(uuid.uuid4())
        self.active[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)

    async def send_to(self, client_id: str, message: dict):
        ws = self.active.get(client_id)
        if ws:
            await ws.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for ws in list(self.active.values()):
            await ws.send_text(data)
    
    async def RequestPlayersInfo(self):
        players_info = []
        players_info.append(Player1.toDict())
        players_info.append(Player2.toDict())
        players_info.append(Player3.toDict())
        players_info.append(Player4.toDict())
        await self.broadcast({"type": "request_players_info", "players": players_info, "turn": TURNO})

manager = ConnectionManager()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    client_ids.append(client_id)
    # comunico al client il suo id (utile per mandare messaggi mirati)
    await manager.send_to(client_id, {"type": "update_id", "client_id": client_id})
    try:
        while True:
            # opzionale: ricevere messaggi dal client
            msg = await websocket.receive_text()
            print("Ricevuto messaggio: ", msg)
            msg = json.loads(msg)
            if msg["type"] == "register_player":
                key = msg["key"]
                if Player1.key is None:
                    Player1.key = key
                    Player1.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player1.toDict()})
                    await manager.RequestPlayersInfo()
                elif Player2.key is None:
                    Player2.key = key
                    Player2.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player2.toDict()})
                    await manager.RequestPlayersInfo()
                elif Player3.key is None:
                    Player3.key = key
                    Player3.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player3.toDict()})
                    await manager.RequestPlayersInfo()
                elif Player4.key is None:
                    Player4.key = key
                    Player4.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player4.toDict()})
                    await manager.RequestPlayersInfo()
            elif msg["type"] == "request_players_info":
                await manager.RequestPlayersInfo()
            elif msg["type"] == "game_action":
                TURNO += 1
                if TURNO >= 4:
                    TURNO = 0


    except WebSocketDisconnect:
        manager.disconnect(client_id)
        if Player1.client_id == client_id:
            Player1.key = None
            Player1.client_id = None
        elif Player2.client_id == client_id:
            Player2.key = None
            Player2.client_id = None
        elif Player3.client_id == client_id:
            Player3.key = None
            Player3.client_id = None
        elif Player4.client_id == client_id:
            Player4.key = None
            Player4.client_id = None









if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)