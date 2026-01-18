from fastapi import Depends, FastAPI, Request
#from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import random
from fastapi.websockets import WebSocket, WebSocketDisconnect, WebSocketState
import json
from typing import Dict
import uuid
import numpy as np #replaceable for random.choice without replacement
from fastapi.templating import Jinja2Templates
from functools import lru_cache
import asyncio
import time
from pathlib import Path

VERSION="1.4"

@lru_cache(maxsize=1)
def asset_manifest():
    p = Path("static/dist/manifest.json")
    return json.loads(p.read_text(encoding="utf-8"))

history = {}
talk_keys = {}
ambassador_position = "step_58"
ambassador_is_captured = False
GAME_UID = str(uuid.uuid4())

def moveAmbassador(to_step):
    global ambassador_position
    ambassador_position = f"step_{to_step}"

def setAmbassadorCaptured(captured):
    global ambassador_is_captured
    ambassador_is_captured = captured

NUM_WHITE = 2
NUM_BLACK = 2
NUM_RED = 2
NUM_BLUE = 2
NUM_YELLOW = 1
NUM_TOTAL = NUM_WHITE + NUM_BLACK + NUM_RED + NUM_BLUE + NUM_YELLOW

def profetizza():
    profezia = ['white'] * NUM_WHITE + ['black'] * NUM_BLACK + ['red'] * NUM_RED + ['blue'] * NUM_BLUE + ['yellow'] * NUM_YELLOW
    random.shuffle(profezia)
    return profezia[:3]

def generateTalkKey():
    return str(uuid.uuid4())

TURNO = None
orders = []

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

BODYTYPES = ['tall','short','medium','large']
COLORS =  ['red','blue','green','yellow']
MISSIONS = ["A","B","C","D"]
PERSONALITY = ["Lord Fiddlebottom", "Colonel Bubble", "Madame Tsatsa", "Agent X"]

associations = []

steps = json.load(open("static/steps.json"))

class Player:
    def __init__(self, player_turn, bodytype = None, color=None, mission=None, personality=None, key=None):
        self.player_turn = player_turn
        self.bodytype = bodytype
        self.color = color
        self.mission = mission
        self.personality = personality
        self.key = key
        self.client_id = None
        self.starting = False
        self.positions = []
        self.captured = []
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
            "positions": self.positions,
            "player_turn": self.player_turn,
            "captured": self.captured
        }
    def movePiece(self, from_step, to_step):
        if from_step in self.positions:
            self.positions[self.positions.index(from_step)] = to_step
            return True
        return False
    def getPieceFromPosition(self, step):
        return self.positions[self.positions.index(step)+4]
    def getStepFromPiece(self, piece):
        return self.positions[self.positions.index(piece)-4]
    def getPieceIDFromPosition(self, step):
        color = self.color
        piece = self.getPieceFromPosition(step)
        return f"{color}_{piece}"
    def __str__(self):
        return f"Player {self.player_turn} - Color: {self.color}, Body: {self.bodytype}, Mission: {self.mission}, Personality: {self.personality}, Key: {self.key}, Positions: {self.positions}"
    def __repr__(self):
        return self.__str__()

Player1 = None
Player2 = None
Player3 = None
Player4 = None
Players = None

def createNewPlayers():
    global TURNO
    global orders
    global Player1, Player2, Player3, Player4, Players
    global history, talk_keys, ambassador_position, ambassador_is_captured, GAME_UID
    history = {}
    talk_keys = {}
    ambassador_position = "step_58"
    ambassador_is_captured = False
    GAME_UID = str(uuid.uuid4())
    Player1 = Player(1)
    Player2 = Player(2)
    Player3 = Player(3)
    Player4 = Player(4)
    Players = [Player1, Player2, Player3, Player4]
    bodies = np.random.choice(BODYTYPES, size=4, replace=False)
    colors = np.random.choice(COLORS, size=4, replace=False)
    missions = np.random.choice(MISSIONS, size=4, replace=False)
    personalities = np.random.choice(PERSONALITY, size=4, replace=False)
    # TODO: fix starting player randomization, now it's 1 for testing
    orders = [int(i) for i in np.random.choice([1,2,3,4], size=4, replace=False)]
    orders = [1,2,3,4]  # for testing
    starting = orders[0]
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
    history = { TURNO: {}}

createNewPlayers()

templates = Jinja2Templates(directory=".")
SUPPORTED_LANG = ["it","en"]
DEFAULT_LANG = "en"

def pick_language(request: Request):
    # 1) query param ?lang=it
    lang = request.query_params.get("lang")
    if lang in SUPPORTED_LANG:
        return lang

    # 2) cookie lang=it
    lang = request.cookies.get("lang")
    if lang in SUPPORTED_LANG:
        return lang

    # 3) Accept-Language
    header = request.headers.get("accept-language", "")
    candidates = [p.split(";")[0].strip() for p in header.split(",") if p.strip()]
    for c in candidates:
        base = c.split("-")[0]
        if c in SUPPORTED_LANG:
            return c
        if base in SUPPORTED_LANG:
            return base

    return DEFAULT_LANG

@lru_cache(maxsize=16)
def load_dict(lang: str) -> dict:
    with open(f"i18n/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_locale(request: Request) -> str:
    return pick_language(request)

def make_t(lang: str):
    d = load_dict(lang)
    def t(key: str, **kwargs) -> str:
        # fallback: if key is missing, show the key (helps with debugging)
        text = d.get(key, f"[{key}]")
        # support parameters: "hello_user": "Ciao {name}"
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return t

@app.get("/")
async def read_root(request: Request, lang: str = Depends(get_locale)):
    #return HTMLResponse(open("index.html").read())
    t = make_t(lang)
    d = load_dict(lang)
    manifest = asset_manifest()
    return templates.TemplateResponse("index.html", {"request": request, "t": t, "lang": lang, "I18N": d, "app_bundle_path": manifest["js"], "style_bundle_path": manifest["css"], "version": VERSION})

@app.get("/restart")
async def restart_game():
    global GAME_UID
    GAME_UID = str(uuid.uuid4())
    if Player1.client_id is not None:
        await manager.disconnect(Player1.client_id)
    if Player2.client_id is not None:
        await manager.disconnect(Player2.client_id)
    if Player3.client_id is not None:
        await manager.disconnect(Player3.client_id)
    if Player4.client_id is not None:
        await manager.disconnect(Player4.client_id)
    createNewPlayers()
    return "OK"
   

class ConnectionManager:
    def __init__(self):
        # client_id -> websocket
        self.active: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self.SEND_TIMEOUT = 5 #seconds
        self.game_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_id = str(uuid.uuid4())
        async with self._lock:
            self.active[client_id] = websocket
        return client_id

    async def disconnect(self, client_id: str):
        async with self._lock:
            ws = self.active.pop(client_id, None)
        if ws and ws.client_state != WebSocketState.DISCONNECTED:
            await ws.close()

    async def safe_send_text(self, client_id, data: str):
        async with self._lock:
            ws = self.active.get(client_id)
        try:
            await asyncio.wait_for(ws.send_text(data), timeout=self.SEND_TIMEOUT)
            return True
        except Exception as e:
            print(f"Error sending message to client: {e}")
            await self.disconnect(client_id=client_id)
            return False

    async def send_to(self, client_id: str, message: dict):
        #await ws.send_text(json.dumps(message))
        return await self.safe_send_text(client_id, json.dumps(message))

    def getPositionsData(self):
        return {
            Player1.color: {
                "pieces": Player1.positions,
                "captured": Player1.captured
            },
            Player2.color: {
                "pieces": Player2.positions,
                "captured": Player2.captured
            },
            Player3.color: {
                "pieces": Player3.positions,
                "captured": Player3.captured
            },
            Player4.color: {
                "pieces": Player4.positions,
                "captured": Player4.captured
            },
            "ambassador": {
                "pieces": int(ambassador_position.split("_")[1]),
                "captured": ambassador_is_captured
            }
        }

    async def sendPositionsTo(self, client_id: str):
        positions = self.getPositionsData()
        await self.send_to(client_id, {"type": "update_positions", "positions": positions, "last_move": history[TURNO].get("last_move", None), "turn": TURNO})
    
    async def sendPositionsToAll(self):
        positions = self.getPositionsData()
        await self.broadcast({"type": "update_positions", "positions": positions, "last_move": history[TURNO].get("last_move", None), "turn": TURNO})

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        async with self._lock:
            clients_ids = list(self.active.keys())
        #for ws in clients:
        #    await ws.send_text(data)
        await asyncio.gather(*[self.safe_send_text(client_id=client_id, data=data) for client_id in clients_ids], return_exceptions=True)
    
    async def RequestPlayersInfo(self):
        players_info = []
        players_info.append(Player1.toDict())
        players_info.append(Player2.toDict())
        players_info.append(Player3.toDict())
        players_info.append(Player4.toDict())
        await self.broadcast({"type": "request_players_info", "players": players_info, "turn": TURNO, **history[TURNO]})

manager = ConnectionManager()

PING_EVERY = 15
PONG_TIMEOUT = 10

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    global TURNO
    client_id = await manager.connect(websocket)
    print(f"Client {client_id} connected")
    last_pong = None
    async def heartbeat():
        nonlocal last_pong
        try:
            while True:
                await asyncio.sleep(PING_EVERY)
                if last_pong is not None and time.monotonic() - last_pong > (PING_EVERY + PONG_TIMEOUT):
                    print(f"Client {client_id} timed out (no pong received)")
                    try:
                        await manager.disconnect(client_id)
                    finally:
                        return
                print("Sending ping to client ", client_id)
                await manager.send_to(client_id, {"type": "ping"})
        except Exception as e:
            print("Errore generico in hearbeat: ", e)
            return
    hb_task = asyncio.create_task(heartbeat())

    # Tell client its ID
    await manager.send_to(client_id, {"type": "update_id", "client_id": client_id, "game_uid": GAME_UID})
    try:
        while True:
            msg = await websocket.receive_text()
            print("Ricevuto messaggio: ", msg)
            msg = json.loads(msg)
            if msg["type"] == "register_player":
                key = msg["key"]
                player = list(filter(lambda p: p.key == key, Players))
                if len(player) > 0:
                    player = player[0]
                    player.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": player.toDict()})
                    #await manager.RequestPlayersInfo()
                    #await manager.sendPositionsTo(client_id)
                    continue
                if Player1.key is None:
                    Player1.key = key
                    Player1.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player1.toDict()})
                    #await manager.RequestPlayersInfo()
                    #await manager.sendPositionsTo(client_id)
                elif Player2.key is None:
                    Player2.key = key
                    Player2.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player2.toDict()})
                    #await manager.RequestPlayersInfo()
                    #await manager.sendPositionsTo(client_id)
                elif Player3.key is None:
                    Player3.key = key
                    Player3.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player3.toDict()})
                    #await manager.RequestPlayersInfo()
                    #await manager.sendPositionsTo(client_id)
                elif Player4.key is None:
                    Player4.key = key
                    Player4.client_id = client_id
                    await manager.send_to(client_id, {"type": "register_player", "player_info": Player4.toDict()})
                    await manager.RequestPlayersInfo()
                    #await manager.sendPositionsTo(client_id)
            elif msg["type"] == "request_players_info":
                await manager.RequestPlayersInfo()
                await manager.sendPositionsTo(client_id)
                continue
            elif msg["type"] == "ping":
                await manager.send_to(client_id, {"type": "ping"})
            elif msg["type"] == "pong":
                last_pong = time.monotonic()
                continue
                #await manager.send_to(client_id, {"type": "pong"})
            elif msg["type"] == "test":
                await manager.send_to(client_id, {"type": "test", "data": "Test received"})
            elif msg["type"] == "__can_move_piece":
                def checkLandMove(from_step, to_step):
                    return f"step_{to_step}" in steps["connections"][f"step_{from_step}"]["land"]
                def checkSeaMove(from_step, to_step):
                    return f"step_{to_step}" in steps["connections"][f"step_{from_step}"]["sea"]
                piece_id = msg["data"]["piece_id"]
                piece_color = piece_id.split("_")[0]
                to_step = int(msg["data"]["to_step"])
                from_step = int(msg["data"]["from_step"])
                using_move = msg["data"]["using_move"]
                move_index = msg["data"]["move_index"]
                player_key = msg["data"]["player_key"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                other_players_position = []
                for p in Players:
                    if p.key != player_key:
                        other_players_position += p.positions
                if piece_color != player.color and using_move != "black":
                    await manager.send_to(client_id, {"type": "__can_move_piece", "status": "wrong_color"})
                    continue
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "__can_move_piece", "status": "not_your_turn"})
                    continue
                async with manager.game_lock:
                    if history[TURNO].get("talks", None) is not None:
                        betweens = []
                        for talk in history[TURNO]["talks"]:
                            betweens = talk["between"]
                        if piece_id in betweens:
                            await manager.send_to(client_id, {"type": "__can_move_piece", "status": "cannot_move_after_capture"})
                            continue
                if (\
                    # Yellow move
                    (((checkSeaMove(from_step, to_step) or checkLandMove(from_step, to_step)) and using_move == "yellow") \
                    # Black move
                    or ((checkSeaMove(from_step, to_step) or checkLandMove(from_step, to_step)) and using_move == "black" and piece_color == "ambassador" and (to_step in player.positions or to_step not in other_players_position)) \
                    # Red move
                    or (checkLandMove(from_step, to_step) and using_move == "red") \
                    # Blue move
                    or (checkSeaMove(from_step, to_step) and using_move == "blue")) \
                    # Check prophecy usage
                    and len(history[TURNO]["prophecy_used"]) <3 \
                    # Check destination is free from player pieces
                    and to_step not in player.positions):
                    print("MOVE CHECK PASSED")
                    print(steps["connections"][f"step_{from_step}"])
                    print("Checking move for player key: ", player_key)
                    print("Piece ID: ", piece_id)
                    print("From step: ", from_step)
                    print("To step: ", to_step)
                    print("Using move: ", using_move)
                    print("Move index: ", move_index)
                    async with manager.game_lock:
                        history[TURNO]["prophecy_used"].append(move_index)
                        history[TURNO].setdefault("talks", [])
                    # Case if capture other pieces or ambassador step into one of its player position or player into ambassador position
                    if to_step in other_players_position or f"step_{to_step}" == ambassador_position or (using_move=="black" and to_step in player.positions):
                        if to_step in other_players_position:
                            print(f"step_{to_step} occupied by another player, removing piece from the board")
                            other_player = list(filter(lambda p: to_step in p.positions, Players))[0]
                            async with manager.game_lock:
                                history[TURNO]["talks"].append({"type": "piece_captured", "from_step": from_step, "to_step": to_step, "using_move": using_move, "piece_id": piece_id, "between": [piece_id, other_player.getPieceIDFromPosition(to_step)], "between_ids": [player.key, other_player.key], "capture_key": f"__{generateTalkKey()}"})
                                other_player.captured.append(other_player.getPieceIDFromPosition(to_step))
                            #player.movePiece(from_step, to_step)
                            if to_step == ambassador_position:
                                setAmbassadorCaptured(True)
                            #if piece_id == "ambassador_ambassador":
                            #    setAmbassadorCaptured(True)
                        elif f"step_{to_step}" == ambassador_position or (using_move=="black" and to_step in player.positions):
                            print(f"step_{to_step} is ambassador position, capturing ambassador")
                            async with manager.game_lock:
                                history[TURNO]["talks"].append({"type": "piece_captured", "from_step": from_step, "to_step": to_step, "using_move": using_move, "piece_id": piece_id, "between": [piece_id, "ambassador_ambassador"], "between_ids": [player.key, "ambassador_player"], "capture_key": f"__{generateTalkKey()}"})
                            setAmbassadorCaptured(True)
                            #moveAmbassador(to_step)
                            #player.movePiece(from_step, to_step)
                    if using_move == "black":
                        moveAmbassador(to_step)
                    else:
                        player.movePiece(from_step, to_step)
                    async with manager.game_lock:
                        history[TURNO]["last_move"] = {"piece_id": piece_id, "from_step": from_step, "to_step": to_step, "using_move": using_move}
                    await manager.send_to(client_id, {"type": "__can_move_piece", "status": "ok", **history[TURNO]})
                    await manager.sendPositionsToAll()
                else:
                    if using_move == "red" and not checkLandMove(from_step, to_step):
                        await manager.send_to(client_id, {"type": "__can_move_piece", "status": "invalid_land_move"})
                    elif using_move == "blue" and not checkSeaMove(from_step, to_step):
                        await manager.send_to(client_id, {"type": "__can_move_piece", "status": "invalid_sea_move"})
                    else:
                        print(f"step_{to_step} not in connections of step_{from_step}")
                        await manager.send_to(client_id, {"type": "__can_move_piece", "status": "invalid_move"})
                    continue
            elif msg["type"] == "__start_turn":
                player_key = msg["data"]["player_key"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "__start_turn", "status": "not_your_turn", **history[TURNO]})
                    continue
                elif history[TURNO].get("turn", None) == "not_finished":
                    await manager.send_to(client_id, {"type": "__start_turn", "status": "turn_not_finished", **history[TURNO]})
                    continue
                else:
                    async with manager.game_lock:
                        history[TURNO].setdefault("talks", [])
                    prophecy_result = profetizza()
                    print("Profetizza result: ", prophecy_result)
                    await manager.send_to(client_id, {"type": "__start_turn", "status": "ok", "prophecy": prophecy_result, "turn": "not_finished", "prophecy_used": []})
                    async with manager.game_lock:
                        history[TURNO] = {"player": player.player_turn, "prophecy": prophecy_result, "turn": "not_finished", "prophecy_used": []}
            elif msg["type"] == "__action":
                action_type = msg["data"]["action_type"]
                piece_id = msg["data"]["piece_id"]
                piece_color = piece_id.split("_")[0]
                player_key = msg["data"]["player_key"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                if piece_id == "ambassador_ambassador" and msg["data"]["ambassador"] is True:
                    other_player = list(filter(lambda p: p.color == msg["data"]["color_with_ambassador"], Players))[0]
                else:
                    other_player = list(filter(lambda p: p.color == piece_color, Players))[0]
                print("BETWEEN PLAYERS:")
                print(player)
                print(other_player)
                betweens = []
                async with manager.game_lock:
                    for talk in history[TURNO]["talks"]:
                        betweens+= talk["between"]
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "__action", "status": "not_your_turn", **history[TURNO]})
                    continue
                elif action_type not in ["what", "who"]:
                    await manager.send_to(client_id, {"type": "__action", "status": "invalid_action_type", **history[TURNO]})
                    continue
                elif other_player.key == player.key:
                    await manager.send_to(client_id, {"type": "__action", "status": "cannot_action_own_piece", **history[TURNO]})
                    continue
                elif piece_id not in betweens:
                    await manager.send_to(client_id, {"type": "__action", "status": "piece_not_captured_this_turn", **history[TURNO]})
                    continue
                else:
                    async with manager.game_lock:
                        talk_key = f"__{generateTalkKey()}"
                        talk_keys[talk_key] = {"from_player_client_id": other_player.client_id, "to_player_client_id": client_id, "from_player": player.player_turn, "action_type": action_type, "piece_id": piece_id}
                    await manager.send_to(other_player.client_id, {"type": "action_talk", "action_type": action_type, "piece_id": piece_id, "from_player": player.player_turn, "from_player_color": player.color, "talk_key": talk_key})
                    await manager.send_to(client_id, {"type": "__action", "status": "ok", **history[TURNO], "talk_key": talk_key})
                    others_players = list(filter(lambda p: p.client_id != client_id and p.client_id != other_player.client_id, Players))
                    for p in others_players:
                        await manager.send_to(p.client_id, {"type": "info_action_talk", "action_type": action_type, "piece_id": piece_id, "from_player": player.player_turn, "from_player_color": player.color, "to_player": other_player.player_turn, "to_player_color": other_player.color})
            elif msg["type"] in list(talk_keys.keys()):
                if msg["status"] == "waiting":
                    continue
                data = msg["answer"]
                await manager.send_to(talk_keys[msg["type"]]["to_player_client_id"], {"type": msg["type"],"status": msg["status"], "data": data, "from_player": talk_keys[msg["type"]]["from_player"], "talk_key": msg["type"]})
                async with manager.game_lock:
                    talk_keys.pop(msg["type"], None)
            elif msg["type"] == "__can_free_piece":
                piece_id = msg["piece_id"]
                player_key = msg["player_key"]
                to_step = msg["to_step"]
                capture_key = msg["capture_key"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                other_players = list(filter(lambda p: p.key != player_key, Players))
                other_players_position = []
                for p in other_players:
                    other_players_position += p.positions
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "__can_free_piece", "status": "not_your_turn", **history[TURNO]})
                    continue
                elif int(to_step) in other_players_position or int(to_step) in player.positions:
                    await manager.send_to(client_id, {"type": "__can_free_piece", "status": "position_occupied", **history[TURNO]})
                    continue
                else:
                    async with manager.game_lock:
                        if piece_id == "ambassador_ambassador" and steps["steps"][f"step_{to_step}"].get("class",None) is None:
                            await manager.send_to(client_id, {"type": "__can_free_piece", "status": "invalid_ambassador_position", **history[TURNO]})
                            continue
                        if piece_id == "ambassador_ambassador" and to_step not in player.positions and to_step not in other_players_position:
                            moveAmbassador(to_step)
                            setAmbassadorCaptured(False)
                        else:
                            other_p = list(filter(lambda p: p.color == piece_id.split("_")[0], Players))[0]
                            other_p.movePiece(other_p.getStepFromPiece(piece_id.split("_")[1]), to_step)
                            other_p.captured.remove(piece_id)
                        history[TURNO]["talks"].pop(next(i for i,talk in enumerate(history[TURNO]["talks"]) if talk.get("capture_key", None) == capture_key))
                        history[TURNO]["last_move"] = {"piece_id": piece_id, "from_step": "captured", "to_step": to_step, "using_move": "free"}
                    await manager.send_to(client_id, {"type": "__can_free_piece", "status": "ok", **history[TURNO]})
                    await manager.sendPositionsToAll()
            elif msg["type"] == "end_turn":
                player_key = msg["data"]["player_key"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "end_turn", "status": "not_your_turn", **history[TURNO]})
                    continue
                else:
                    async with manager.game_lock:
                        history[TURNO]["turn"] = "finished"
                    await manager.send_to(client_id, {"type": "end_turn", "status": "ok", **history[TURNO]})
                    async with manager.game_lock:
                        history.pop(TURNO)
                        TURNO = orders[(orders.index(TURNO)+1)%len(orders)]
                        history[TURNO] = {}
                    await manager.sendPositionsToAll()

    except WebSocketDisconnect:
        hb_task.cancel()
        print(f"Client {client_id} disconnected")
        await manager.disconnect(client_id)
        if Player1.client_id == client_id:
            #Player1.key = None
            Player1.client_id = None
        elif Player2.client_id == client_id:
            #Player2.key = None
            Player2.client_id = None
        elif Player3.client_id == client_id:
            #Player3.key = None
            Player3.client_id = None
        elif Player4.client_id == client_id:
            #Player4.key = None
            Player4.client_id = None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)