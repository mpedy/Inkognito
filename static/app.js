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

class Player{
    constructor(name,color,bodytype, personality){
        this.id = null;
        this.name=name;
        this.color=color;
        this.bodytype=bodytype;
        this.personality=personality;
    }
}
class Communication{
    constructor(){
        // Quando ci sarà una chiave univoca per il gioco (room):
        //this.ws = new WebSocket("ws://"+window.location.hostname+":"+window.location.port+"/ws_"+window.location.pathname);
        this.ws = new WebSocket("ws://"+window.location.hostname+":"+window.location.port+"/ws");
        this.connections = [];
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            for(let conn of this.connections){
                if(message.type === conn.type){
                    conn.onMessage(this, message);
                }
            }
        }
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
        this.key = (Math.random().toString(36).substring(2) + Math.random().toString(36).substring(2) + Math.random().toString(36).substring(2)).substring(0,21);
        this.setCookie("game_key", this.key, 365);
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

class Game{
    constructor(){
        this.comm = new Communication();
        this.cookieManager = new CookieManager();
        this.me = new Player();
        this.me.name = "ME";
        this.players = [this.me, new Player(),new Player(),new Player()];
        this.playerUI = new PlayerUI(this.players[0], "player_info_ui");
        this.otherPlayersUI = [
            new PlayerUI(this.players[1], "player_info_ui_1"),
            new PlayerUI(this.players[2], "player_info_ui_2"),
            new PlayerUI(this.players[3], "player_info_ui_3")
        ];
        this.players[1].playerUI = this.otherPlayersUI[0];
        this.players[2].playerUI = this.otherPlayersUI[1];
        this.players[3].playerUI = this.otherPlayersUI[2];
        this.key = null;
        this.setup();
    };
    setup(){
        // Come genero una chiave univoca per il giocatore lato client?
        this.me.key = this.cookieManager.getCookie("game_key");
        this.comm.addConnection("register_player",(comm,message)=>{
            this.me.bodytype = BodyTypes[message["player_info"]["bodytype"].toUpperCase()];
            this.me.color = Colors[message["player_info"]["color"].toUpperCase()];
            this.me.personality = Personality[message["player_info"]["personality"]];
            this.playerUI.setColor(this.me.color);
            this.playerUI.setBodyType(this.me.bodytype);
            this.playerUI.setPersonality(this.me.personality);
            this.playerUI.setImg(message["player_info"]["color"], message["player_info"]["bodytype"], message["player_info"]["mission"]);
        });
        this.comm.sendMessage(JSON.stringify({
            "type": "register_player",
            "key": this.cookieManager.getCookie("game_key")
        }));
        // Request players info from server
        this.comm.addConnection("request_players_info",(comm,message)=>{
            for(var p=0; p < message["players"].length; p++){
                if( this.me.key !== message["players"][p]["key"] ){
                    this.players[p].id = message["players"][p]["id"];
                    this.players[p].name = message["players"][p]["name"];
                    this.players[p].color = Colors[message["players"][p]["color"].toUpperCase()];
                    this.players[p].bodytype = BodyTypes[message["players"][p]["bodytype"].toUpperCase()];
                    this.players[p].personality = Personality[message["players"][p]["personality"]];
                    this.players[p].playerUI.setColor(this.players[p].color);
                    this.players[p].playerUI.setBodyType(this.players[p].bodytype);
                }
            }
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