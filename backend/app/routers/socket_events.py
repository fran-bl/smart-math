import datetime
from urllib import request

from app.main import sio

from ..db import SessionLocal
from ..models.game import Game
from ..models.users import User
from ..models.game_players import GamePlayers
from ..models.users import User
from .socket_auth import authenticate_socket_with_token
from ..db import db
from ..models.questions import Question

questions = {}

@sio.event
async def connect(sid, environ, auth):
    token = None

    # Get token from auth payload (Socket.IO client auth option)
    if auth and isinstance(auth, dict):
        token = auth.get("token")

    # Fallback: Authorization header
    if not token:
        token = environ.get("HTTP_AUTHORIZATION")
        # `authenticate_socket_with_token` will normalize Bearer prefix if present

    if not token or not str(token).strip():
        return False

    user = await authenticate_socket_with_token(str(token).strip())

    if not user:
        return False

    # Attach user to socket session
    await sio.save_session(
        sid,
        {
            "user_id": str(user.id),
            "role": user.role,
            "username": user.username,
        },
    )

    print("Socket connected:", user.username)


@sio.event
async def teacherJoin(sid, data):
    session = await sio.get_session(sid)

    if session["role"] != "teacher":
        await sio.emit("error", {"message": "Unauthorized"}, to=sid)
        return

    db = SessionLocal()

    game = (
        db.query(Game)
        .filter(
            Game.id == data["game_id"],
            Game.teacher_id == session["user_id"],
            Game.status == "lobby",
        )
        .first()
    )

    if not game:
        await sio.emit("error", {"message": "Invalid game"}, to=sid)
        return

    await sio.enter_room(sid, str(game.id))
    await emit_players(game.id)


# student join
@sio.event
async def handle_join_game(sid, data):
    session = await sio.get_session(sid)

    if session["role"] != "student":
        await sio.emit("error", {"message": "Students only"}, to=sid)
        return

    db = SessionLocal()

    game = (
        db.query(Game)
        .filter(Game.game_code == data["game_code"], Game.status == "lobby")
        .first()
    )

    if not game:
        await sio.emit("error", {"message": "Game not found"}, to=sid)
        return

    user_id = session["user_id"]

    user = db.query(User).filter(User.id == user_id, User.role == "student").first()

    if not user:
        await sio.emit("error", {"message": "User not found"}, to=sid)
        return

    player = db.query(GamePlayers).filter_by(game_id=game.id, user_id=user.id).first()

    if player:
        player.socket_id = sid
        player.is_active = True
        player.left_at = None
    else:
        db.add(
            GamePlayers(
                game_id=game.id,
                user_id=user.id,
                socket_id=sid,
            )
        )

    db.commit()

    # Store game_id on the socket session so we can cleanly handle disconnects
    await sio.save_session(
        sid,
        {
            **session,
            "game_id": str(game.id),
        },
    )

    await sio.enter_room(sid, str(game.id))
    await emit_players(game.id)


async def emit_players(game_id):
    db = SessionLocal()

    players = (
        db.query(User.username)
        .join(GamePlayers, GamePlayers.user_id == User.id)
        .filter(GamePlayers.game_id == game_id, GamePlayers.is_active.is_(True))
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

    # Prefer DB lookup by socket_id; fallback to session if needed
    player = (
        db.query(GamePlayers)
        .filter(GamePlayers.socket_id == sid, GamePlayers.is_active.is_(True))
        .first()
    )

    if not player:
        try:
            session = await sio.get_session(sid)
        except Exception:
            return

        user_id = session.get("user_id") if session else None
        game_id = session.get("game_id") if session else None
        if not user_id or not game_id:
            return

        player = (
            db.query(GamePlayers)
            .filter(
                GamePlayers.user_id == user_id,
                GamePlayers.game_id == game_id,
                GamePlayers.is_active.is_(True),
            )
            .first()
        )

    if not player:
        return

    player.is_active = False
    player.left_at = datetime.datetime.utcnow()
    db.commit()

    await emit_players(player.game_id)


async def get_socket_user(sid):
    session = await sio.get_session(sid)
    return session



@sio.event
async def handle_start_game(data):
    db = SessionLocal()
    room_id = data["room_id"]
    topic_id = data["selectedTopic"]["topic_id"]

    game = Game.query.filter_by(game_id=room_id).first()
    if not game:
        sio.emit("error", {"message": "Game not found"}, to=request.sid)
        return

    clients = list(sio.server.manager.rooms["/"].get(room_id, {}).keys())
    valid_clients = clients[1:] #prva vrijednost je admin socket, to nam ne treba

    if room_id not in questions:
        questions[room_id] = {}

    # Je li izabrano multiple ili single room
    if game.room_option == "multiple" and game.players_per_room:
        # Podijeli clients u grupe prema players_per_room
        groups = [
            valid_clients[i:i + game.players_per_room]
            for i in range(0, len(valid_clients), game.players_per_room)
        ]
        if len(groups) > 1 and len(groups[-1]) < 2:
            last_group = groups.pop()
            for i, player in enumerate(last_group):
                groups[i % len(groups)].append(player)

        print(f"Adjusted Grouping Players: {groups}")

        # Emit grupe adminu
        admin_groups = []
        for idx, group in enumerate(groups):
            admin_groups.append({
                "group_id": idx + 1,
                "players": [
                    {"name": User.query.filter_by(socket_id=client).first().username, "id": client}
                    for client in group
                ]
            })

        sio.emit("groupsDistribution", {"groups": admin_groups}, to=clients[0])


        for idx, group in enumerate(groups):
            new_game = Game(
                teacher_id=game.teacher_id,
                topic_selected=game.topic_selected,
                start_time=datetime.now(),
                is_locked=True,
                game_code=f"{game.game_code}_group_{idx + 1}",
                mode=game.mode,
            )
            db.add(new_game)
            db.commit()


            new_game_id = str(new_game.game_id)

            if new_game_id not in questions:
                questions[new_game_id] = {}

            for client in group:
                student = db.query(User).filter_by(socket_id=client).first()
                if student:
                    student.game_id = new_game_id
                    db.commit()

                await sio.enter_room(client, str(new_game_id))

                user_questions = generate_questions(topic_id)
                questions[str(new_game_id)][client] = [task["task_id"] for task in user_questions]

                await sio.emit(
                    "receiveQuestions",
                    {
                        "questions": user_questions,
                        "game_id": str(new_game_id),
                        "topic_id": topic_id,
                    },
                    to=client,
                )


    else:
        # Single-room (default)
        for client in clients[1:]:
            user_questions = generate_questions(topic_id)
            questions[room_id][client] = [task["task_id"] for task in user_questions]

            sio.emit(
                "receiveQuestions",
                {"questions": user_questions, "game_id": room_id, "topic_id": topic_id},
                to=client,
            )

#TODO: change question ?

#TODO: handle player answered


@sio.event
async def endGame(sid, data):
    db = SessionLocal()

    print("Received data in handle_leave_game:", data)
    try:
        room_id = data["room_id"]

        questions.pop(room_id, None) 

        game = (db.query(Game).filter((Game.game_id == room_id)).first())

        if game:
            
                game.end_time = datetime.now()
                db.commit()

        student = (
            db.query(User).filter(User.socket_id == sid).first()
        )
        if student:
            name = student.username

        await sio.emit("gameEnded", {"winner": name}, room=room_id)

    except Exception as e:
            db.rollback()
            await sio.emit("error", {"message": f"Database error {str(e)}"}, room=room_id)
            return
    finally:
        db.close()



#TODO: POPRAVI OVO DA ODGOVARA NASOJ BAZI
def generate_questions(topic_id):
    if topic_id:
        written_ans = aliased(WrittenAnswer)
        numerical_ans = aliased(NumericalAnswer)
        mc_ans = aliased(MultipleChoiceAnswer)

        queries = []

        for diff in ["easy", "medium", "high"]:
            query = (
                db.session.query(Question, written_ans, numerical_ans, mc_ans)
                .filter(Task.topic_id == topic_id, Task.difficulty == diff)
                .outerjoin(written_ans, Task.task_id == written_ans.task_id)
                .outerjoin(numerical_ans, Task.task_id == numerical_ans.task_id)
                .outerjoin(mc_ans, Task.task_id == mc_ans.task_id)
                .order_by(func.random())
                .limit(3)
            )
            queries.append(query)

        sample = queries[0]
        for q in queries[1:]:
            sample = sample.union_all(q)

        ret = []

        for task, written_data, numerical_data, mc_data in sample.all():
            obj = {
                "task_id": str(task.task_id),
                "question": task.question,
                "difficulty": task.difficulty,
                "answer": {},
            }

            if written_data:
                obj["answer"] = {
                    "type": "written",
                    "correct_answer": written_data.correct_answer,
                }
            elif numerical_data:
                obj["answer"] = {
                    "type": "numerical",
                    "correct_answer": numerical_data.correct_answer,
                }
            else:
                obj["answer"] = {
                    "type": "multiple choice",
                    "option_a": mc_data.option_a,
                    "option_b": mc_data.option_b,
                    "option_c": mc_data.option_c,
                    "correct_answer": mc_data.correct_answer,
                }

            ret.append(obj)

    return ret