const Colors = Object.freeze({
    RED: Symbol('red'),
    BLUE: Symbol('blue'),
    GREEN: Symbol('green'),
    YELLOW: Symbol('yellow')
});
const BodyTypes = Object.freeze({
    TALL: Symbol('tall'),
    SHORT: Symbol('short'),
    MEDIUM: Symbol('medium'),
    LARGE: Symbol('large')
});
const Personality = Object.freeze({
    "Lord Fiddlebottom": Symbol("Lord Fiddlebottom"),
    "Colonel Bubble": Symbol("Colonel Bubble"),
    "Madame Tsatsa": Symbol("Madame Tsatsa"),
    "Agent X": Symbol("Agent X")
})
const MOVES = Object.freeze({
    "white": Symbol("white"),
    "black": Symbol("black"),
    "red": Symbol("red"),
    "blue": Symbol("blue"),
    "yellow": Symbol("yellow")
});

class Player{
    constructor(name,color,bodytype, personality, mission){
        this.id = null;
        this.name=name;
        this.color=color;
        this.bodytype=bodytype;
        this.personality=personality;
        this.mission=mission;
    }
}
class Communication{
    constructor(){
        // Quando ci sarà una chiave univoca per il gioco (room):
        //this.ws = new WebSocket("ws://"+window.location.hostname+":"+window.location.port+"/ws_"+window.location.pathname);
        this.ws = this.startWebSocket()
        this.connections = [];
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            for(let conn of this.connections){
                if(message.type === conn.type){
                    conn.onMessage(this, message);
                }
            }
        }
        this.ws.onclose = (event) => {
            console.log("WebSocket closed, attempting to reconnect in 3 seconds...");
            setTimeout(() => {
                this.ws = this.startWebSocket();
            }, 3000);
        };
    };
    startWebSocket(){
        return new WebSocket("ws://"+window.location.hostname+":"+window.location.port+"/ws");
    }
    startPingPong(interval){
        setInterval(() => {
            this.sendCraftedMessage("ping");
        }, interval);
    };
    sendMessage(message){
        if(this.ws.readyState !== WebSocket.OPEN){
            setTimeout(() => {
                this.sendMessage(message);
            }, 500)
        }else{
            this.ws.send(message);
        }
    };
    sendCraftedMessage(type, data=[]){
        let message = {type: type, data: data};
        if(this.ws.readyState !== WebSocket.OPEN){
            setTimeout(() => {
                this.sendCraftedMessage(type, data);
            }, 500);
        }else{
            this.ws.send(JSON.stringify(message));
        }
    }
    sendAndWait(type, data=[]) {// type must start with "__"
        return new Promise((resolve, reject) => {
            if(type.startsWith("__") === false){
                console.error("sendAndWait type must start with '__'");
                return reject("sendAndWait type must start with '__'");
            }
            const handler = event => {
                this.ws.removeEventListener("message", handler);
                resolve(event.data);
            };
            this.ws.addEventListener("message", handler);
            this.ws.send(JSON.stringify({type: type, data: data}));
        });
    };
    addConnection(type, handler){
        for(let conn of this.connections){
            if(conn.type === type){
                conn.onMessage = handler;
                return;
            }
        }
        this.connections.push({type: type, onMessage: handler});
    }
    removeConnection(type){
        this.connections = this.connections.filter(conn => conn.type !== type);
    }

}

class CookieManager{
    constructor(){
        if(this.getCookie("game_key") === ""){
            this.key = (Math.random().toString(36).substring(2) + Math.random().toString(36).substring(2) + Math.random().toString(36).substring(2)).substring(0,21);
            debugger;
            this.setCookie("game_key", this.key, 365);
        }
    };
    setCookie(cname, cvalue, exdays) {
        const d = new Date();
        d.setTime(d.getTime() + (exdays*24*60*60*1000));
        let expires = "expires="+ d.toUTCString();
        document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
    }
    getCookie(cname) {
        let name = cname + "=";
        let decodedCookie = decodeURIComponent(document.cookie);
        let ca = decodedCookie.split(';');
        for(let i = 0; i <ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) == ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) == 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }
    deleteCookie(cname) {
        document.cookie = cname + "=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    }
}

class PlayerUI{
    constructor(player, uiElementId){
        this.player = player;
        this.uiElement = document.getElementById(uiElementId);
    };
    setColor(color){
        this.uiElement.classList.remove("color_red","color_blue","color_green","color_yellow");
        switch(color){
            case Colors.RED:
                this.uiElement.classList.add("color_red");
                break;
            case Colors.BLUE:
                this.uiElement.classList.add("color_blue");
                break;
            case Colors.GREEN:
                this.uiElement.classList.add("color_green");
                break;
            case Colors.YELLOW:
                this.uiElement.classList.add("color_yellow");
                break;
        }
    };
    setBodyType(bodytype){
        this.uiElement.classList.remove("body_tall","body_short","body_medium","body_large");
        switch(bodytype){
            case BodyTypes.TALL:
                this.uiElement.classList.add("body_tall");
                break;
            case BodyTypes.SHORT:
                this.uiElement.classList.add("body_short");
                break;
            case BodyTypes.MEDIUM:
                this.uiElement.classList.add("body_medium");
                break;
            case BodyTypes.LARGE:
                this.uiElement.classList.add("body_large");
                break;
        }
    };
    setPersonality(personality){
        this.uiElement.querySelector("span").innerHTML = personality.toString().split("Symbol(")[1].split(")")[0];
    };
    setImg(color, bodytype, mission){
        let src = "static/" + color+"_"+bodytype+".png";
        this.uiElement.querySelector("#player_img").src = src;
        this.uiElement.querySelector("#player_mission").src="static/mission_"+mission+".png";
    }
}

class GameUI{
    constructor(game){
        this.steps = document.getElementById("steps");
        this.base_color = {
            "red": document.querySelectorAll(".step_red"),
            "green": document.querySelectorAll(".step_green"),
            "blue": document.querySelectorAll(".step_blue"),
            "yellow": document.querySelectorAll(".step_yellow")
        }
        this.pieces = {};
        this.pieces_width = 30;
        this.board = undefined;
        this.game = game;
        this.prophecyUIElem = document.getElementById("prophecy_ui");
        this.prophecyUIElem.querySelector("#start_turn").addEventListener("click", this.game.startTurn.bind(this.game));
        this.pieces_img_src = {
            "red_tall": "static/red_tall.png",
            "red_short": "static/red_short.png",
            "red_medium": "static/red_medium.png",
            "red_large": "static/red_large.png",
            "blue_tall": "static/blue_tall.png",
            "blue_short": "static/blue_short.png",
            "blue_medium": "static/blue_medium.png",
            "blue_large": "static/blue_large.png",
            "green_tall": "static/green_tall.png",
            "green_short": "static/green_short.png",
            "green_medium": "static/green_medium.png",
            "green_large": "static/green_large.png",
            "yellow_tall": "static/yellow_tall.png",
            "yellow_short": "static/yellow_short.png",
            "yellow_medium": "static/yellow_medium.png",
            "yellow_large": "static/yellow_large.png"
        }
        this.prisonUIElem = document.getElementById("captured_pieces");
        this.prisonUIElem.querySelectorAll("div.capturedpiece").forEach(elem => {
            elem.addEventListener("click", this.game.handlers["capturedPieceClicked"].bind(this.game, elem.getAttribute("data-piece-id"), elem));
        });
        this.whatBtn = document.getElementById("what");
        this.whoBtn = document.getElementById("who");
        this.whatBtn.addEventListener("click", this.game.handlers["whatOrWhoClicked"].bind(this.game, "what"));
        this.whoBtn.addEventListener("click", this.game.handlers["whatOrWhoClicked"].bind(this.game, "who"));
    };
    popolateTrueCards(){
        this.myCardsElem = document.getElementById("my_cards");
        this.myCardsElem_bodytypes = this.myCardsElem.querySelector("#bodytypes");
        this.myCardsElem_personalities = this.myCardsElem.querySelector("#personalities");
        this.myCardsElem_truecards = this.myCardsElem.querySelector("#truecards");
        let color = this.game.getMyColor();
        let bodytype = this.game.getMyBodytype();
        let personality = this.game.getMyPersonality();
        let mission = this.game.me.mission;
        for(let i of Object.keys(BodyTypes)){
            this.myCardsElem_bodytypes.querySelector("img[data-bodytype='"+i+"']").src = "static/"+color+"_"+i.toLowerCase()+".png";
        }
        for(let i of Object.keys(Personality)){
            this.myCardsElem_personalities.querySelector("img[data-personality='"+i+"']").src = "static/"+color+"_"+i.toLowerCase().replaceAll(" ","_")+".png";
        }
        this.myCardsElem_truecards.querySelector("img[data-truecard='mission']").src = "static/mission_"+mission+".png";
        this.myCardsElem_truecards.querySelector("img[data-truecard='bodytype']").src = "static/white_"+bodytype+".png";
        this.myCardsElem_truecards.querySelector("img[data-truecard='personality']").src = "static/white_"+personality.toLowerCase().replaceAll(" ","_")+".png";
    };
    highlightPiece(pieceElem){
        pieceElem.children[0].classList.toggle("selected");
        pieceElem.children[1].classList.toggle("selected");
    }
    addAmbassyPiece(step="58"){
        this.board.getElementById("step_58");
        let pieceId = "ambassador_ambassador";
        let pieceElem = this.board.getElementById(pieceId);
        pieceElem.classList.add("piece");
        if(!this.pieces[pieceId]){
            pieceElem.addEventListener("click", this.game.handlers["pieceClicked"].bind(this.game, pieceId, pieceElem));
            this.pieces[pieceId] = pieceElem;
        }
        let stepElem = this.board.querySelector("#step_"+step);
        if(stepElem){
            pieceElem.style.transform = `translate(${stepElem.getAttribute("cx") - this.pieces_width/2}px, ${stepElem.getAttribute("cy") - this.pieces_width/2}px)`;
            pieceElem.setAttribute("data-step", step);
        }
    }
    addPieceToStep(color, bodytype, step, board){
        if(!this.board){
            this.board = board;
        }
        let pieceId = color+"_"+bodytype;
        let pieceElem = board.getElementById(pieceId);
        pieceElem.classList.add("piece");
        if(!this.pieces[pieceId]){
            pieceElem.addEventListener("click", this.game.handlers["pieceClicked"].bind(this.game, pieceId, pieceElem));
            this.pieces[pieceId] = pieceElem;
        }
        let stepElem = board.querySelector("#step_"+step);
        if(stepElem){
            pieceElem.style.transform = `translate(${stepElem.getAttribute("cx") - this.pieces_width/2}px, ${stepElem.getAttribute("cy") - this.pieces_width/2}px)`;
            pieceElem.setAttribute("data-step", step);
        }
    };
    movePieceFromStepToStep(color, bodytype, toStep){
        let pieceId = color+"_"+bodytype;
        let pieceElem = this.board.getElementById(pieceId);
        let stepElem = this.board.querySelector("#"+toStep);
        pieceElem.setAttribute("data-step", toStep.split("step_")[1]);
        pieceElem.style.transform = `translate(${stepElem.getAttribute("cx") - this.pieces_width/2}px, ${stepElem.getAttribute("cy") - this.pieces_width/2}px)`;
    };
    showProphecyResults(results){
        let balls = this.prophecyUIElem.querySelectorAll(".prophecy_ball");
        for(let i=0; i<balls.length; i++){
            balls[i].style.backgroundColor = results[i];
            balls[i].setAttribute("data-color", results[i]);
            if(results[i] !== "white"){
                balls[i].addEventListener("click", function(){this.game.balls[i].getAttribute("data-used") === "1" ? null : this.game.selectMove(i)}.bind(this, i));
            }else{
                balls[i].style.cursor = "not-allowed";
            }
        }
    };
    useProphecy(mv){
        if(!this.game.balls){
            this.game.balls = this.prophecyUIElem.querySelectorAll(".prophecy_ball");
        }
        this.game.balls[mv].style.opacity = "0.3";
        this.game.balls[mv].style.cursor = "not-allowed";
        this.game.balls[mv].setAttribute("data-used", "1");
    };
    selectMove(mv){
        if(!this.game.balls){
            this.game.balls = this.prophecyUIElem.querySelectorAll(".prophecy_ball");
        }
        this.game.balls[mv].classList.toggle("selected_move");
        for(let i=0; i<this.game.balls.length; i++){
            if(i !== mv){
                this.game.balls[i].classList.remove("selected_move");
            }
        }
    };
    capturePiece(pieceId){
        let pieceElem = this.board.getElementById(pieceId);
        pieceElem.classList.add("captured");
        document.getElementById(`${pieceId}_captured`).classList.remove("hidden");
        this.game.capturedPieces.push(pieceId);
        //TODO: ambassador capture handling
    };
    showCardsForTalk(action_type, piece_id, from_player, talk_key){
        document.getElementById("talk_dialog").classList.remove("hidden");
        document.getElementById("talk_dialog_action_type").innerText = action_type;
        document.getElementById("talk_dialog_piece_id").innerText = piece_id;
        document.getElementById("talk_dialog_from_player").innerText = from_player;
        document.getElementById("talk_dialog_talk_key").innerText = talk_key;
    };

}

class Game{
    constructor(){
        this.setupHandlers();
        this.comm = new Communication();
        this.cookieManager = new CookieManager();
        this.me = new Player();
        this.me.name = "ME";
        this.players = [this.me, new Player(),new Player(),new Player()];
        this.playerUI = new PlayerUI(this.players[0], "player_info_ui");
        this.gameUI = new GameUI(this);
        this.otherPlayersUI = [
            new PlayerUI(this.players[1], "player_info_ui_1"),
            new PlayerUI(this.players[2], "player_info_ui_2"),
            new PlayerUI(this.players[3], "player_info_ui_3")
        ];
        this.players[1].playerUI = this.otherPlayersUI[0];
        this.players[2].playerUI = this.otherPlayersUI[1];
        this.players[3].playerUI = this.otherPlayersUI[2];
        this.key = null;
        this.debug = true;
        this.pieceClicked = null;
        this.moves = [];
        this.moveSelected = null;
        this.balls = document.querySelectorAll(".prophecy_ball");
        this.capturedPieces = [];
        this.setup();
    };
    getMyColor(){
        return this.me.color.toString().split("Symbol(")[1].split(")")[0];
    };
    getMyBodytype(){
        return this.me.bodytype.toString().split("Symbol(")[1].split(")")[0];
    };
    getMyPersonality(){
        return this.me.personality.toString().split("Symbol(")[1].split(")")[0];
    }
    setupHandlers(){
        this.handlers = {
            "stepClicked": function(stepIndex, stepElem){
                console.log("Step clicked: "+stepIndex);
                if(true){//Condition on prophecy results, for now leave it true
                    if(this.pieceClicked && this.moves[this.moveSelected] != null){
                        this.comm.sendAndWait("__can_move_piece", {
                            "piece_id": this.pieceClicked.id,
                            "from_step": this.pieceClicked.getAttribute("data-step"),
                            "to_step": stepIndex,
                            "using_move": this.balls[this.moveSelected].getAttribute("data-color"),
                            "move_index": this.moveSelected,
                            "player_key": this.me.key
                        }).then((response) => {
                            response = JSON.parse(response);
                            if(response["status"] == "ok"){
                                this.useMove(this.moveSelected);
                                this.gameUI.movePieceFromStepToStep(
                                    this.pieceClicked.id.split("_")[0],
                                    this.pieceClicked.id.split("_")[1],
                                    stepElem.id
                                );
                                if(response["talks"].length > 0){
                                    for(var talk of response["talks"]){
                                        this.gameUI.capturePiece(talk["between"][1]);
                                    }
                                }
                            }else{
                                console.log(response);
                            }
                            this.gameUI.highlightPiece(this.pieceClicked);
                            this.pieceClicked = null;
                        })
                    }

                }
            },
            "pieceClicked": function(pieceId, pieceElem){
                console.log("Piece clicked: "+pieceId);
                if(this.pieceClicked && this.pieceClicked !== pieceElem && this.moveSelected !== null){
                    return this.handlers["stepClicked"].bind(this)(pieceElem.getAttribute("data-step"), this.gameUI.board.querySelector("#step_"+pieceElem.getAttribute("data-step")));
                }
                this.gameUI.highlightPiece(pieceElem);
                if(!this.pieceClicked){
                    this.pieceClicked = pieceElem;
                }else{
                    if(this.pieceClicked === pieceElem){
                        this.pieceClicked = null;
                    }else{
                        this.gameUI.highlightPiece(this.pieceClicked);
                        this.pieceClicked = pieceElem;
                    }
                }
            },
            "capturedPieceClicked": function(pieceId, pieceElem){
                console.log("Captured piece clicked: ", pieceId);
                if(!this.capturedPieceSelected){
                    this.capturedPieceSelected = pieceElem;
                    document.getElementById("capture_choice").classList.remove("hidden");
                }else{
                    if(this.capturedPieceSelected === pieceElem){
                        this.capturedPieceSelected = null;
                        document.getElementById("capture_choice").classList.add("hidden");
                    }else{
                        this.capturedPieceSelected.classList.toggle("selected");
                        this.capturedPieceSelected = pieceElem;
                        document.getElementById("capture_choice").classList.remove("hidden");
                    }
                }
                pieceElem.classList.toggle("selected");
            },
            "whatOrWhoClicked": function(action_type){
                let pieceId = this.capturedPieceSelected.getAttribute("data-piece-id");
                console.log("What clicked for captured piece: ", pieceId);
                let comm = this.comm;
                this.comm.sendAndWait("__action", {
                    "action_type": action_type,
                    "piece_id": pieceId,
                    "player_key": this.me.key
                }).then(function(response){
                    response = JSON.parse(response);
                    console.log(response);
                    if(response["status"] == "ok"){
                        //TODO: update UI accordingly
                        // Response contains key for waiting for player answer, meanwhile server messages other players with my requests
                        comm.sendAndWait("__" + response["talk_key"]).then(function(final_response){
                            final_response = JSON.parse(final_response);
                            console.log(final_response);
                        })
                    }
                })
            },
            "action_talk": function(message){
                console.log("Talk action received: ", message);
                action_type = message["action_type"]
                piece_id = message["piece_id"]
                from_player = message["from_player"]
                talk_key = message["talk_key"]
                // Show dialog to answer to talk
                this.gameUI.showCardsForTalk(action_type, piece_id, from_player, talk_key);
            }
        };
    }
    selectMove(mv){
        console.log("Selected move: ", mv);
        if(this.moveSelected == mv){
            this.moveSelected = null;
        }else{
            this.moveSelected = mv;
        }
        this.gameUI.selectMove(mv);
    }
    endTurn(){
        this.comm.sendCraftedMessage("end_turn");
    }
    startTurn(){
        this.comm.sendAndWait("__start_turn", {
            "player_key": this.me.key
        }).then((response) => {
            response = JSON.parse(response);
            if(response["status"] == "not_your_turn"){
                return;
            }
            if(response["status"] == "ok"){
                this.moves = response["prophecy"];
                console.log("Available moves: ", this.moves);
                this.gameUI.showProphecyResults(this.moves);
            }else{
                console.log(response);
                this.moves = response["prophecy"];
                this.gameUI.showProphecyResults(this.moves);
                for(var i of response["prophecy_used"]){
                    this.useMove(i);
                }
                if(response["talks"].length > 0){
                    for(var talk of response["talks"]){
                        this.gameUI.capturePiece(talk["between"][1]);
                    }
                }
            }
        });
    }
    useMove(mv){
        this.moves[mv] = null;
        this.gameUI.useProphecy(mv);
    }
    generateSteps(){
        this.board = document.getElementById("board");
        this.board.addEventListener("load", () => {
            this.gameUI.board = this.board.contentDocument;
            for(var i=1; i<=58; i++){
                let stepElem = this.gameUI.board.getElementById("step_"+i);
                stepElem.style.cursor = "pointer";
                stepElem.addEventListener("click", this.handlers["stepClicked"].bind(this, i, stepElem));
            }
            for(var i=1; i<=8; i++){
                let textElem = this.gameUI.board.getElementById("txt_"+i);
                textElem.style.pointerEvents = "none";
                let textElem1 = this.gameUI.board.getElementById("txt_"+i+"_1");
                textElem1.style.pointerEvents = "none";
            }
        });
        fetch("static/steps.json").then(response => response.json()).then(data => {
           this.connections = data["connections"];
        });
    };
    setup(){
        this.generateSteps();
        this.me.key = this.cookieManager.getCookie("game_key");
        this.comm.addConnection("pong", (comm, message)=>{
            console.log("Pong received");
        })
        this.comm.addConnection("ping", (comm, message)=>{
            console.log("Ping received: ", message)
            comm.sendCraftedMessage("pong");
        })
        this.comm.startPingPong(600000);
        this.comm.addConnection("register_player",(comm,message)=>{
            this.me.bodytype = BodyTypes[message["player_info"]["bodytype"].toUpperCase()];
            this.me.color = Colors[message["player_info"]["color"].toUpperCase()];
            this.me.personality = Personality[message["player_info"]["personality"]];
            this.me.mission = message["player_info"]["mission"];
            this.playerUI.setColor(this.me.color);
            this.playerUI.setBodyType(this.me.bodytype);
            this.playerUI.setPersonality(this.me.personality);
            this.playerUI.setImg(message["player_info"]["color"], message["player_info"]["bodytype"], message["player_info"]["mission"]);
            this.gameUI.popolateTrueCards();
        });
        this.comm.sendMessage(JSON.stringify({
            "type": "register_player",
            "key": this.cookieManager.getCookie("game_key")
        }));
        // Request players info from server
        this.comm.addConnection("request_players_info",(comm,message)=>{
            let index = 0;
            for(var p=0; p < message["players"].length; p++){
                if( this.me.key !== message["players"][p]["key"] ){
                    index += 1;
                    this.players[index].id = message["players"][index]["id"];
                    this.players[index].name = message["players"][index]["name"];
                    this.players[index].color = Colors[message["players"][index]["color"].toUpperCase()];
                    this.players[index].bodytype = BodyTypes[message["players"][index]["bodytype"].toUpperCase()];
                    this.players[index].personality = Personality[message["players"][index]["personality"]];
                    this.players[index].playerUI.setColor(this.players[index].color);
                    this.players[index].playerUI.setBodyType(this.players[index].bodytype);
                }
                for(var i=0; i<4; i++){
                    this.gameUI.addPieceToStep(message["players"][p]["color"], message["players"][p]["positions"][i+4], message["players"][p]["positions"][i], this.board.contentDocument);
                }
            }
            this.gameUI.addAmbassyPiece();
        });
        this.comm.sendCraftedMessage("request_players_info");
    };
}


var game = new Game();

document.querySelectorAll('#canovaccio>table>tbody>tr>td>input').forEach(elem => {
    elem.addEventListener('focus', (event) => {
        var text = elem.getAttribute("data-text");
        if( text === null){
            elem.setAttribute("data-text", "x");
            elem.value = "x";
            document.activeElement.blur();
        }else if(text == "x"){
            elem.setAttribute("data-text", "o");
            elem.value = "o";
            document.activeElement.blur();
        }else if(text == "o"){
            elem.setAttribute("data-text", "");
            elem.value = "";
            document.activeElement.blur();
        }
    });
});