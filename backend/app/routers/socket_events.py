import datetime
import random
from typing import Annotated
from urllib import request

from app.main import sio

from ..db import SessionLocal
from ..models.game import Game
from ..models.users import User
from ..models.game_players import GamePlayers
from ..models.users import User
from .socket_auth import authenticate_socket_with_token
from sqlalchemy.orm import Session
from ..models.questions import Question
from ..models.mc_answer import McAnswer
from ..models.num_answer import NumAnswer
from ..models.wri_answer import WriAnswer
from ..models.rounds import Round
from ..models.attempts import Attempt
from sqlalchemy import func, Numeric



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
    students = clients[1:] #prva vrijednost je admin socket, to nam ne treba

    if room_id not in questions:
        questions[room_id] = {}


    #generiraj za svakog studenta njegova pitanja i započni njegovu rundu u bazi
    for sid in students[1:]:
        session = await sio.get_session(sid)

        if not session or session["role"] != "student":
            continue

        user_id = session["user_id"]
        student = (db.query(User).filter((User.id == user_id)).first())
        current_difficulty = student.current_difficulty
        user_questions = generate_questions(topic_id, current_difficulty)


        # Create round
        round_obj = Round(
            user_id=user_id,
            game_id=game.id,
            question_count=len(user_questions),
        )
        db.add(round_obj)
        db.commit()
        db.refresh(round_obj)


        #TODO: promijeni task
        questions[room_id][sid] = {
            "user_id": user_id,
            "task_ids": [q["task_id"] for q in user_questions],
        }

        await sio.emit(
            "receiveQuestions",
            {"questions": user_questions, "game_id": game.id, "topic_id": topic_id},
            to=sid,
        )



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



DIFFICULTY_DISTRIBUTION = {
    1: {1: 10},
    2: {1: 3, 2: 5, 3: 2},
    3: {2: 2, 3: 6, 4: 2},
    4: {3: 2, 4: 6, 5: 2},
    5: {4: 5, 5: 5},
}

def generate_questions(db: Session, topic_id, current_difficulty: int, limit: int =10):
    
    if not topic_id: 
        return []


    distribution = DIFFICULTY_DISTRIBUTION.get(current_difficulty)
    if not distribution:
        return []
    

    selected_questions = []
    #radi samo ako imamo dovoljno pitanja u bazi
    for difficulty, count in distribution.items():
        rows = (
            db.query(Question)
            .filter(
                Question.topic_id == topic_id,
                Question.difficulty == difficulty,
            )
            .order_by(func.random())
            .limit(count)
            .all()
        )

        selected_questions.extend(rows)

    #promijesaj da tezine pitanja ne idu redom
    random.shuffle(selected_questions)

    result = []

    for q in selected_questions[:limit]:
        item = {
            "question_id": str(q.id),
            "question": q.text,
            "difficulty": q.difficulty,  
            "type": q.type,
            "answer": {},
        }

        if q.type == "num":
            ans = (
                db.query(NumAnswer)
                .filter(NumAnswer.question_id == q.id)
                .first()
            )
            if ans:
                item["answer"] = {
                    "type": "numerical",
                    "correct_answer": ans.correct_answer,
                }

        elif q.type == "mcq":
            ans = (
                db.query(McAnswer)
                .filter(McAnswer.question_id == q.id)
                .first()
            )
            if ans:
                item["answer"] = {
                    "type": "multiple_choice",
                    "option_a": ans.option_a,
                    "option_b": ans.option_b,
                    "option_c": ans.option_c,
                    "correct_answer": ans.correct_answer,
                }

        elif q.type == "wri":
            ans = (
                db.query(WriAnswer)
                .filter(WriAnswer.question_id == q.id)
                .first()
            )
            if ans:
                item["answer"] = {
                    "type": "written",
                    "correct_answer": ans.correct_answer,
                }

        result.append(item)
    
    return result


#FRONTEND SALJE:
#{
#  "round_id": "...",
#  "question_id": "...",
#  "is_correct": true,
#  "time_spent_secs": 8,
#  "hints_used": 1,
#  "num_attempts": 2
#}
#EVENT ZA HANDLEANJE SVAKOG ODGOVORA NA PITANJE
@sio.event
async def submit_answer(sid, data):
    db: Session = SessionLocal()

    session = await sio.get_session(sid)
    if not session:
        return

    user_id = session["user_id"]

    attempt = Attempt(
        user_id=user_id,
        question_id=data["question_id"],
        round_id=data["round_id"],
        is_correct=data["is_correct"],
        num_attempts=data.get("num_attempts", 1),
        time_spent_secs=data.get("time_spent_secs", 0),
        hints_used=data.get("hints_used", 0),
    )

    db.add(attempt)
    db.commit()


#EVENT ZA GOTOVU RUNDU SVAKOG UCENIKA
@sio.event
async def finish_round(sid, data):
    db = SessionLocal()
    finalize_round(db, data["round_id"])



def finalize_round(db: Session, round_id):
    stats = (
        db.query(
            func.count(Attempt.id),
            func.avg(Attempt.time_spent_secs),
            func.sum(Attempt.hints_used),
            func.avg(func.cast(Attempt.is_correct, Numeric)),
        )
        .filter(Attempt.round_id == round_id)
        .one()
    )

    total, avg_time, hints, accuracy = stats

    round_obj = db.query(Round).filter(Round.id == round_id).one()

    round_obj.end_ts = func.now()
    round_obj.avg_time_secs = avg_time or 0
    round_obj.hint_rate = (hints / total) if total else 0
    round_obj.accuracy = accuracy or 0

    db.commit()


#TODO: kako računamo student_stats, što je xp etc.