import datetime
import random
import uuid

from app.main import sio
from sqlalchemy import Numeric, func
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models.attempts import Attempt
from ..models.game import Game
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


def _finish_game(db: Session, game: Game) -> None:
    """Mark game as finished and deactivate all active players."""
    game.status = "finished"
    game.end_time = datetime.datetime.utcnow()
    db.add(game)

    active_players = (
        db.query(GamePlayers)
        .filter(GamePlayers.game_id == game.id, GamePlayers.is_active.is_(True))
        .all()
    )
    for p in active_players:
        p.is_active = False
        p.left_at = datetime.datetime.utcnow()
        db.add(p)

    db.commit()


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
    try:
        # Accept joining both lobby and started games (teacher page needs to reconnect after start).
        # Parse ids defensively because socket session stores them as strings.
        teacher_id = uuid.UUID(str(session["user_id"]))
        game_id = uuid.UUID(str(data["game_id"]))

        game = (
            db.query(Game)
            .filter(
                Game.id == game_id,
                Game.teacher_id == teacher_id,
            )
            .first()
        )

        if not game:
            await sio.emit("error", {"message": "Invalid game"}, to=sid)
            return
        if game.status == "finished":
            await sio.emit("error", {"message": "Game already finished"}, to=sid)
            return

        await sio.enter_room(sid, str(game.id))
        # Store game_id for teacher so we can close the lobby if teacher disconnects.
        mode = None
        if isinstance(data, dict):
            mode = data.get("mode")
        await sio.save_session(sid, {**session, "game_id": str(game.id), "mode": mode})
        await emit_players(game.id)
    finally:
        db.close()


# student join
@sio.event
async def handle_join_game(sid, data):
    session = await sio.get_session(sid)

    if session["role"] != "student":
        await sio.emit("error", {"message": "Students only"}, to=sid)
        return

    db = SessionLocal()
    try:
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

        player = (
            db.query(GamePlayers).filter_by(game_id=game.id, user_id=user.id).first()
        )

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
                    is_active=True,
                    left_at=None,
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

        # Ack to the joining student so the UI can stop "connecting" even if updatePlayers is delayed.
        await sio.emit("joinedGame", {"game_id": str(game.id)}, to=sid)
    finally:
        db.close()


@sio.event
async def joinGame(sid, data):
    """
    Frontend emits `joinGame`.
    Keep the existing implementation in `handle_join_game` and expose this wrapper
    so students don't get stuck in infinite "Povezivanje..." when the event name mismatches.
    """
    return await handle_join_game(sid, data)


async def emit_players(game_id):
    db = SessionLocal()
    try:
        rows = (
            db.query(
                User.id.label("user_id"),
                User.username.label("username"),
                User.current_difficulty.label("level"),
                StudentStats.xp.label("xp"),
            )
            .join(GamePlayers, GamePlayers.user_id == User.id)
            .outerjoin(StudentStats, StudentStats.user_id == User.id)
            .filter(GamePlayers.game_id == game_id, GamePlayers.is_active.is_(True))
            .all()
        )

        players_simple = [r.username for r in rows]

        # Rank players by XP (desc). If stats row doesn't exist, treat as 0.
        ranked = sorted(rows, key=lambda r: int(r.xp or 0), reverse=True)
        rank_by_user_id = {str(r.user_id): idx + 1 for idx, r in enumerate(ranked)}

        players_detailed = [
            {
                "user_id": str(r.user_id),
                "username": r.username,
                "level": int(r.level or 1),
                "xp": int(r.xp or 0),
                "rank": int(rank_by_user_id.get(str(r.user_id), 0) or 0),
            }
            for r in rows
        ]

        await sio.emit(
            "updatePlayers",
            {"players": players_simple, "playersDetailed": players_detailed},
            room=str(game_id),
        )
    finally:
        db.close()


@sio.event
async def disconnect(sid):
    db = SessionLocal()
    try:
        # IMPORTANT:
        # A teacher may "disconnect" simply by navigating from the lobby modal to the /teacher/game page,
        # which creates a new socket connection. Auto-closing the lobby here causes false "game finished"
        # and kicks students out. We only close games via explicit events (closeLobby/endGame).
        try:
            session = await sio.get_session(sid)
        except Exception:
            session = None

        # If teacher leaves the *game page* (mode == 'game'), end the game for everyone.
        # (We intentionally do NOT auto-finish on lobby disconnect, because navigating to the game page
        # creates a new socket and would otherwise end the lobby immediately.)
        if session and session.get("role") == "teacher":
            if session.get("mode") == "game" and session.get("game_id"):
                try:
                    game_id = uuid.UUID(str(session["game_id"]))
                    teacher_id = uuid.UUID(str(session["user_id"]))
                except Exception:
                    return

                game = (
                    db.query(Game)
                    .filter(Game.id == game_id, Game.teacher_id == teacher_id)
                    .first()
                )
                if game and game.status != "finished":
                    _finish_game(db, game)
                    await sio.emit(
                        "gameClosed", {"game_id": str(game.id)}, room=str(game.id)
                    )
            return

        # Prefer DB lookup by socket_id; fallback to session if needed
        player = (
            db.query(GamePlayers)
            .filter(GamePlayers.socket_id == sid, GamePlayers.is_active.is_(True))
            .first()
        )

        if not player:
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
    finally:
        db.close()


@sio.event
async def closeLobby(sid, data):
    """Teacher closes the lobby modal before/without playing. End game for all students."""
    session = await sio.get_session(sid)
    if not session or session.get("role") != "teacher":
        return

    game_id_raw = data.get("game_id") if isinstance(data, dict) else None
    if not game_id_raw:
        return

    db = SessionLocal()
    try:
        try:
            game_id = uuid.UUID(str(game_id_raw))
            teacher_id = uuid.UUID(str(session["user_id"]))
        except Exception:
            return

        game = (
            db.query(Game)
            .filter(Game.id == game_id, Game.teacher_id == teacher_id)
            .first()
        )
        if not game or game.status == "finished":
            return

        _finish_game(db, game)
        await sio.emit("gameClosed", {"game_id": str(game.id)}, room=str(game.id))
    finally:
        db.close()


@sio.event
async def endGame(sid, data):
    """Teacher ends an active game explicitly (from game page)."""
    session = await sio.get_session(sid)
    if not session or session.get("role") != "teacher":
        return

    game_id_raw = data.get("game_id") if isinstance(data, dict) else None
    if not game_id_raw:
        game_id_raw = session.get("game_id")
    if not game_id_raw:
        return

    db = SessionLocal()
    try:
        try:
            game_id = uuid.UUID(str(game_id_raw))
            teacher_id = uuid.UUID(str(session["user_id"]))
        except Exception:
            return

        game = (
            db.query(Game)
            .filter(Game.id == game_id, Game.teacher_id == teacher_id)
            .first()
        )
        if not game or game.status == "finished":
            return

        _finish_game(db, game)
        await sio.emit("gameClosed", {"game_id": str(game.id)}, room=str(game.id))
    finally:
        db.close()


async def get_socket_user(sid):
    session = await sio.get_session(sid)
    return session


@sio.event
async def startGame(sid, data):
    """Teacher starts the game and emits receiveQuestions (with round_id) to each student socket."""
    session = await sio.get_session(sid)
    if not session or session.get("role") != "teacher":
        await sio.emit("error", {"message": "Unauthorized"}, to=sid)
        return

    if not isinstance(data, dict):
        await sio.emit("error", {"message": "Invalid payload"}, to=sid)
        return

    game_id = data.get("game_id")
    topic_id = data.get("topic_id")
    if not game_id or not topic_id:
        await sio.emit("error", {"message": "Missing game_id or topic_id"}, to=sid)
        return

    db = SessionLocal()
    try:
        game = (
            db.query(Game)
            .filter(
                Game.id == game_id,
                Game.teacher_id == session["user_id"],
                Game.status == "lobby",
            )
            .first()
        )
        if not game:
            await sio.emit("error", {"message": "Game not found"}, to=sid)
            return
        game.status = "started"
        db.add(game)
        db.commit()

        room_key = str(game.id)
        if room_key not in questions:
            questions[room_key] = {}

        active = (
            db.query(GamePlayers)
            .filter(GamePlayers.game_id == game.id, GamePlayers.is_active.is_(True))
            .all()
        )

        for gp in active:
            if not gp.socket_id:
                continue
            student = (
                db.query(User)
                .filter(User.id == gp.user_id, User.role == "student")
                .first()
            )
            if not student:
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

            questions[room_key][gp.socket_id] = {
                "user_id": str(student.id),
                "question_ids": [q["question_id"] for q in user_questions],
                "round_id": str(round_obj.id),
            }

            await sio.emit(
                "receiveQuestions",
                {
                    "questions": user_questions,
                    "game_id": str(game.id),
                    "topic_id": str(topic_id),
                    "round_id": str(round_obj.id),
                },
                to=gp.socket_id,
            )

        await sio.emit("gameStarted", {"game_id": str(game.id)}, room=room_key)
    finally:
        db.close()


@sio.event
async def handle_start_game(sid, data):
    # Backwards compatible alias (if any old frontend emits this)
    await startGame(sid, data)


@sio.event
async def endGameLegacy(sid, data):
    """
    Legacy event kept for compatibility with any old clients.
    Prefer `endGame` + `gameClosed` for the current app.
    """
    return


DIFFICULTY_DISTRIBUTION = {
    1: {1: 10},
    2: {1: 3, 2: 5, 3: 2},
    3: {2: 2, 3: 6, 4: 2},
    4: {3: 2, 4: 6, 5: 2},
    5: {4: 5, 5: 5},
}


def generate_questions(db: Session, topic_id, current_difficulty: int, limit: int = 10):
    if not topic_id:
        return []

    distribution = DIFFICULTY_DISTRIBUTION.get(current_difficulty)
    if not distribution:
        return []

    selected_questions = []
    # radi samo ako imamo dovoljno pitanja u bazi
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

    # promijesaj da tezine pitanja ne idu redom
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
            ans = db.query(NumAnswer).filter(NumAnswer.question_id == q.id).first()
            if ans:
                item["answer"] = {
                    "type": "numerical",
                    "correct_answer": ans.correct_answer,
                }

        elif q.type == "mcq":
            ans = db.query(McAnswer).filter(McAnswer.question_id == q.id).first()
            if ans:
                item["answer"] = {
                    "type": "multiple_choice",
                    "option_a": ans.option_a,
                    "option_b": ans.option_b,
                    "option_c": ans.option_c,
                    "correct_answer": ans.correct_answer,
                }

        elif q.type == "wri":
            ans = db.query(WriAnswer).filter(WriAnswer.question_id == q.id).first()
            if ans:
                item["answer"] = {
                    "type": "written",
                    "correct_answer": ans.correct_answer,
                }

        result.append(item)

    return result


# FRONTEND SALJE:
# {
#  "round_id": "...",
#  "question_id": "...",
#  "is_correct": true,
#  "time_spent_secs": 8,
#  "hints_used": 1,
#  "num_attempts": 2
# }
# EVENT ZA HANDLEANJE SVAKOG ODGOVORA NA PITANJE
@sio.event
async def submit_answer(sid, data):
    db: Session = SessionLocal()
    try:
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
    except Exception as e:
        db.rollback()
        await sio.emit("error", {"message": f"Database error {str(e)}"}, to=sid)
        return
    finally:
        db.close()


# dohvati novi batch pitanja
# frontend salje:
# topic_id = data["selectedTopic"]["topic_id"]
# room_id = data["room_id"]
@sio.event
async def fetch_new_batch(sid, data):
    db: Session = SessionLocal()
    try:
        session = await sio.get_session(sid)
        if not session:
            return

        user_id = session["user_id"]
        game_id = session.get("game_id")
        topic_id = data["selectedTopic"]["topic_id"]
        room_id = data["room_id"]

        student = db.query(User).filter((User.id == user_id)).first()
        if not student:
            await sio.emit("error", {"message": "User not found"}, to=sid)
            return

        current_difficulty = student.current_difficulty
        user_questions = generate_questions(db, topic_id, current_difficulty)

        # Create round
        round_obj = Round(
            user_id=user_id,
            game_id=game_id,
            question_count=len(user_questions),
        )
        db.add(round_obj)
        db.commit()
        db.refresh(round_obj)

        if room_id not in questions:
            questions[room_id] = {}

        questions[room_id][sid] = {
            "user_id": str(user_id),
            "question_ids": [q["question_id"] for q in user_questions],
            "round_id": str(round_obj.id),
        }

        await sio.emit(
            "receiveQuestions",
            {
                "questions": user_questions,
                "game_id": str(game_id),
                "topic_id": str(topic_id),
                "round_id": str(round_obj.id),
            },
            to=sid,
        )
    except Exception as e:
        db.rollback()
        await sio.emit("error", {"message": f"Database error {str(e)}"}, to=sid)
        return
    finally:
        db.close()


# EVENT ZA GOTOVU RUNDU SVAKOG UCENIKA
@sio.event
async def finish_round(sid, data):
    db = SessionLocal()
    try:
        session = await sio.get_session(sid)
        if not session:
            return

        user_id = session["user_id"]
        finalize_round(db, data["round_id"], user_id)
    finally:
        db.close()


def finalize_round(db: Session, round_id, user_id):
    student = db.query(User).filter((User.id == user_id)).first()

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

    # create new recommendation based on model prediction and apply it instantly
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

    # student stats
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
        (old_accuracy * old_attempts) + (round_accuracy * round_attempts)
    ) / new_attempts

    # XP (podlozno promjeni ovisi kak se dogovorimo)
    xp_gained = int(round_accuracy * 100)

    stats.total_attempts = new_attempts
    stats.overall_accuracy = new_accuracy
    stats.xp += xp_gained

    db.add(stats)
    db.commit()
