import datetime
from ..models.game_players import GamePlayers
from ..models.users import User
from .socket_auth import authenticate_socket
from ..db import SessionLocal
from ..models.game import Game
from app.main import sio


@sio.event
async def connect(sid, environ):
    token = environ.get("HTTP_AUTHORIZATION")

    if not token:
        return False  

    user = await authenticate_socket(environ)

    if not user:
        return False 

    # Attach user to socket session
    await sio.save_session(sid, {
        "user_id": str(user.id),
        "role": user.role,
        "username": user.username,
    })

    print("Socket connected:", user.username)




@sio.event
async def teacherJoin(sid, data):
    session = await sio.get_session(sid)

    if session["role"] != "teacher":
        await sio.emit("error", {"message": "Unauthorized"}, to=sid)
        return

    db = SessionLocal()

    game = db.query(Game).filter(
        Game.id == data["game_id"],
        Game.teacher_id == session["user_id"],
        Game.status == "lobby"
    ).first()

    if not game:
        await sio.emit("error", {"message": "Invalid game"}, to=sid)
        return

    await sio.enter_room(sid, str(game.id))
    await emit_players(game.id)


#student join
@sio.event
async def joinGame(sid, data):

    session = await sio.get_session(sid)


    if session["role"] != "student":
        await sio.emit("error", {"message": "Students only"}, to=sid)
        return
    
    db = SessionLocal()

    game = db.query(Game).filter(
        Game.game_code == data["game_code"],
        Game.status == "lobby"
    ).first()

    if not game:
        await sio.emit("error", {"message": "Game not found"}, to=sid)
        return


    user_id = session["user_id"]

    user = db.query(User).filter(
        User.id == user_id,
        User.role == "student"
    ).first()

    if not user:
        await sio.emit("error", {"message": "User not found"}, to=sid)
        return

    player = db.query(GamePlayers).filter_by(
        game_id=game.id,
        user_id=user.id
    ).first()

    if player:
        player.socket_id = sid
        player.is_active = True
        player.left_at = None
    else:
        db.add(GamePlayers(
            game_id=game.id,
            user_id=user.id,
            socket_id=sid,
        ))

    db.commit()

    await sio.enter_room(sid, str(game.id))
    await emit_players(game.id)


async def emit_players(game_id):
    db = SessionLocal()

    players = (
        db.query(User.username)
        .join(GamePlayers, GamePlayers.user_id == User.id)
        .filter(
            GamePlayers.game_id == game_id,
            GamePlayers.is_active == True
        )
        .all()
    )

    await sio.emit(
        "updatePlayers",
        {"players": [p.username for p in players]},
        room=str(game_id),
    )


@sio.event
async def disconnect(sid):
    db = SessionLocal()

    player = db.query(GamePlayers).filter(
        GamePlayers.socket_id == sid,
        GamePlayers.is_active == True
    ).first()

    if not player:
        return

    player.is_active = False
    player.left_at = datetime.utcnow()
    db.commit()

    await emit_players(player.game_id)


async def get_socket_user(sid):
    session = await sio.get_session(sid)
    return session

