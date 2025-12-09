from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models.users import User
from ..models.classroom import Classroom
from ..models.questions import Question

router = APIRouter()

@router.get("/count_users", summary="Broj korisnika u bazi")
def count_users(db: Session = Depends(get_db)):
    count = db.query(User).count()
    return {"user_count": count}


@router.get("/count_classrooms")
def count_classrooms(db: Session = Depends(get_db)):
    count = db.query(Classroom).count()
    return {"classroom_count": count}


@router.get("/count_questions")
def count_questions(db: Session = Depends(get_db)):
    count = db.query(Question).count()
    return {"question_count": count}
