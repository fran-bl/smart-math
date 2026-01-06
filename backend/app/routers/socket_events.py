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
#from ..models.mc_answer import McAnswer
from ..models.num_answer import NumAnswer
#from ..models.wri_answer import WriAnswer
from ..models.rounds import Round
from ..models.attempts import Attempt
from sqlalchemy import func, Numeric
from .ml_predict import DifficultyRequest, predict_function
from .ml_feedback import FeedbackRequest, derive_true_label, feedback_function
from ..models.recommendations import Recommendation
from ..models.student_stats import StudentStats



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


        last_round = (
            db.query(Round)
            .filter(Round.user_id == user_id)
            .order_by(Round.round_index.desc())
            .first()
        )

        next_index = 0 if last_round is None else last_round.round_index + 1

        # Create round
        round_obj = Round(
            user_id=user_id,
            game_id=game.id,
            question_count=len(user_questions),
            round_index=next_index,
        )
        db.add(round_obj)
        db.commit()
        db.refresh(round_obj)


        questions[room_id][sid] = {
            "user_id": user_id,
            "question_ids": [q["question_id"] for q in user_questions],
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

#dohvati novi batch pitanja
#frontend salje:
#topic_id = data["selectedTopic"]["topic_id"]
#room_id = data["room_id"]
@sio.event
async def fetch_new_batch(sid, data):
    db: Session = SessionLocal()

    session = await sio.get_session(sid)

    user_id = session["user_id"]
    game_id = session.get("game_id")
    topic_id = data["selectedTopic"]["topic_id"]
    room_id = data["room_id"]
    
    student = (db.query(User).filter((User.id == user_id)).first())
    current_difficulty = student.current_difficulty
    user_questions = generate_questions(topic_id, current_difficulty)


        # Create round
    round_obj = Round(
            user_id=user_id,
            game_id=game_id,
            question_count=len(user_questions),
        )
    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)


      
    questions[room_id][sid] = {
            "user_id": user_id,
            "question_ids": [q["question_id"] for q in user_questions],
        }

    await sio.emit(
            "receiveQuestions",
            {"questions": user_questions, "game_id": game_id, "topic_id": topic_id},
            to=sid,
        )



#EVENT ZA GOTOVU RUNDU SVAKOG UCENIKA
@sio.event
async def finish_round(sid, data):
    db = SessionLocal()
    session = await sio.get_session(sid)

    user_id = session["user_id"]
    finalize_round(db, data["round_id"], user_id)



def finalize_round(db: Session, round_id, user_id):

    student = (db.query(User).filter((User.id == user_id)).first())
    

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
    round_obj.hints = hints
    round_obj.accuracy = accuracy or 0

    db.commit()
    db.refresh(round_obj)

    #call model
    diff_response = predict_function(DifficultyRequest(
            accuracy=round_obj.accuracy,
            avg_time=round_obj.avg_time_secs,
            hints_used=round_obj.hints,
        )
    )

    #Find previous round
    prev_round = (
        db.query(Round)
        .filter(
            Round.user_id == user_id,
            Round.round_index == round_obj.round_index - 1
        )
        .one_or_none()
    )

    if prev_round:
        prev_rec = (
            db.query(Recommendation)
            .filter(
                Recommendation.user_id == user_id,
                Recommendation.round_index == prev_round.round_index,
                Recommendation.true_label.is_(None)
            )
            .one_or_none()
        )

        if prev_rec:
            true_label = derive_true_label(prev_round, round_obj)

            prev_rec.true_label = true_label
            prev_rec.labeled_at = datetime.now()
            db.add(prev_rec)
            db.commit()

            feedback_function(FeedbackRequest(
                    accuracy=prev_round.accuracy,
                    avg_time=prev_round.avg_time_secs,
                    hints_used=prev_round.hints,
                    true_label=true_label,
                    sample_weight=5.0 * prev_rec.confidence
                )
            )

    if diff_response.label == 0:
        rec_text = "down"
        if student.current_difficulty > 1:
            new_diff = student.current_difficulty - 1
    elif diff_response.label == 1:
        rec_text = "same"
        new_diff = student.current_difficulty
    elif diff_response.label == 2:
        rec_text = "up"
        if student.current_difficulty < 5:
            new_diff = student.current_difficulty + 1
    
    #create new recommendation based on model prediction and apply it instantly
    recommendation = Recommendation(
            round_id = round_id,
            user_id=user_id,
            rec = rec_text,
            confidence = diff_response.probabilities.get(diff_response.label, 1),
            prev_difficulty = student.current_difficulty,
            new_difficulty = new_diff,
            round_index = round_obj.round_index
        )
    db.add(recommendation)

    student.current_difficulty = new_diff
    db.add(student)
    db.commit()
    
    #student stats
    round_attempts = round_obj.question_count
    round_accuracy = float(round_obj.accuracy)

    stats = (
        db.query(StudentStats)
        .filter(StudentStats.user_id == round_obj.user_id)
        .one_or_none()
    )

    if not stats:
        stats = StudentStats(
            user_id=round_obj.user_id,
            total_attempts=0,
            overall_accuracy=0,
            xp=0,
        )
        db.add(stats)

    old_attempts = stats.total_attempts
    old_accuracy = float(stats.overall_accuracy or 0)

    new_attempts = old_attempts + round_attempts

    # weighted average accuracy
    new_accuracy = (
        (old_accuracy * old_attempts)
        + (round_accuracy * round_attempts)
    ) / new_attempts

    # XP (podlozno promjeni ovisi kak se dogovorimo)
    xp_gained = int(round_accuracy * 100)

    stats.total_attempts = new_attempts
    stats.overall_accuracy = new_accuracy
    stats.xp += xp_gained

    db.add(stats)
    db.commit()