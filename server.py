from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import random
from fastapi.websockets import WebSocket, WebSocketDisconnect
import json
from typing import Dict
import uuid
import numpy as np #replaceable for random.choice without replacement

history = {}

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

app = FastAPI()
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

BODYTYPES = ['tall','short','medium','large']
COLORS =  ['red','blue','green','yellow']
MISSIONS = ["A","B","C","D"]
PERSONALITY = ["Lord Fiddlebottom", "Colonel Bubble", "Madame Tsatsa", "Agent X"]
client_ids = []

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

Player1 = Player(1)
Player2 = Player(2)
Player3 = Player(3)
Player4 = Player(4)
Players = [Player1, Player2, Player3, Player4]

def createNewPlayers():
    global TURNO
    global history
    bodies = np.random.choice(BODYTYPES, size=4, replace=False)
    colors = np.random.choice(COLORS, size=4, replace=False)
    missions = np.random.choice(MISSIONS, size=4, replace=False)
    personalities = np.random.choice(PERSONALITY, size=4, replace=False)
    # TODO: fix starting player randomization, now it's 1 for testing
    starting = random.randint(1,4)*0+1
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

@app.get("/")
async def read_root():
    return HTMLResponse(open("index.html").read())
   

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
    global TURNO
    client_id = await manager.connect(websocket)
    client_ids.append(client_id)
    # comunico al client il suo id (utile per mandare messaggi mirati)
    await manager.send_to(client_id, {"type": "update_id", "client_id": client_id})
    await manager.broadcast({"type": "game_action", "data": {"turn": TURNO}})
    try:
        while True:
            # opzionale: ricevere messaggi dal client
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
                    await manager.RequestPlayersInfo()
                    continue
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
            elif msg["type"] == "ping":
                await manager.send_to(client_id, {"type": "ping"})
            elif msg["type"] == "pong":
                await manager.send_to(client_id, {"type": "pong"})
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
                    and len(history[TURNO]["prophecy_used"]) <3):
                    print("MOVE CHECK PASSED")
                    print(steps["connections"][f"step_{from_step}"])
                    print("Checking move for player key: ", player_key)
                    print("Piece ID: ", piece_id)
                    print("From step: ", from_step)
                    print("To step: ", to_step)
                    print("Using move: ", using_move)
                    print("Move index: ", move_index)
                    history[TURNO]["prophecy_used"].append(move_index)
                    history[TURNO].setdefault("talks", [])
                    if to_step in other_players_position or (using_move=="black" and to_step in player.positions):
                        print(f"step_{to_step} occupied by another player, removing piece from the board")
                        other_player = list(filter(lambda p: to_step in p.positions, Players))[0]
                        history[TURNO]["talks"].append({"type": "piece_captured", "from_step": from_step, "to_step": to_step, "using_move": using_move, "piece_id": piece_id, "between": [piece_id, other_player.getPieceIDFromPosition(to_step)], "between_ids": [player.key, other_player.key]})
                    player.movePiece(from_step, to_step)
                    await manager.send_to(client_id, {"type": "__can_move_piece", "status": "ok", **history[TURNO]})
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
                history[TURNO].setdefault("talks", [])
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "__start_turn", "status": "not_your_turn", **history[TURNO]})
                    continue
                elif history[TURNO].get("turn", None) == "not_finished":
                    await manager.send_to(client_id, {"type": "__start_turn", "status": "turn_not_finished", **history[TURNO]})
                    continue
                else:
                    prophecy_result = profetizza()
                    prophecy_result = ["yellow", "yellow", "yellow"]  # for testing
                    print("Profetizza result: ", prophecy_result)
                    await manager.send_to(client_id, {"type": "__start_turn", "status": "ok", "prophecy": prophecy_result, "turn": "not_finished", "prophecy_used": []})
                    history[TURNO] = {"player": player.player_turn, "prophecy": prophecy_result, "turn": "not_finished", "prophecy_used": []}
            elif msg["type"] == "__action":
                action_type = msg["data"]["action_type"]
                piece_id = msg["data"]["piece_id"]
                piece_color = piece_id.split("_")[0]
                player_key = msg["data"]["player_key"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                other_player = list(filter(lambda p: p.color == piece_color, Players))[0]
                print("BETWEEN PLAYERS:")
                print(player)
                print(other_player)
                betweens = []
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
                    talk_key = generateTalkKey()
                    await manager.send_to(other_player.client_id, {"type": "action_talk", "action_type": action_type, "piece_id": piece_id, "from_player": player.player_turn, "talk_key": talk_key})
                    await manager.send_to(client_id, {"type": "__action", "status": "ok", **history[TURNO], "talk_key": talk_key})
            elif msg["type"] == "action_response":
                # TODO: to review
                talk_key = msg["data"]["talk_key"]
                response = msg["data"]["response"]
                player_turn = msg["data"]["player_turn"]
                player_key = msg["data"]["player_key"]
                response = msg["data"]["response"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "action_response", "status": "not_your_turn", **history[TURNO]})
                    continue
                else:
                    history[TURNO]["talks"].append({"type": "action_response", "talk_key": talk_key, "response": response})
                    await manager.send_to(list(filter(lambda p: p.player_turn == player_turn, Players))[0].client_id, {"type": "action_response", "status": "ok", "response": response, **history[TURNO]})
            elif msg["type"] == "end_turn":
                player_key = msg["data"]["player_key"]
                player = list(filter(lambda p: p.key == player_key, Players))[0]
                if TURNO != player.player_turn:
                    await manager.send_to(client_id, {"type": "end_turn", "status": "not_your_turn", **history[TURNO]})
                    continue
                else:
                    history[TURNO]["turn"] = "finished"
                    TURNO+=1
                    if TURNO > 4:
                        TURNO = 1
                    await manager.send_to(client_id, {"type": "end_turn", "status": "ok", **history[TURNO]})


    except WebSocketDisconnect:
        manager.disconnect(client_id)
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