import datetime
import random
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.game import Game
from ..models.users import User
from ..routers.auth import get_current_user

router = APIRouter(prefix="/game", tags=["game"])
db_dependency = Annotated[Session, Depends(get_db)]


def generateGameCode():
    letters = "ABCD"

    code = "".join(random.choice(letters) for _ in range(4))
    return code


@router.post("/create-multiplayer-game")
def create_multiplayer_game(
    db: db_dependency, current_user: User = Depends(get_current_user)
):
    game = Game(
        game_code=generateGameCode(),
        teacher_id=current_user.id,
        status="lobby",
        created_at=datetime.datetime.utcnow(),
    )

    try:
        db.add(game)
        db.commit()
        db.refresh(game)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Database error")

    return {
        "game_id": str(game.id),
        "game_code": game.game_code,
    }
