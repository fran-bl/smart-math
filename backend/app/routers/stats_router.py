from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models.users import User
from ..routers.auth import get_current_user
from ..models.student_stats import StudentStats
from pydantic import BaseModel

router = APIRouter(prefix="/stats", tags=["stats"])
db_dependency = Annotated[Session, Depends(get_db)]

class StudentStatsResponse(BaseModel):
    student: str
    total_attempts: int
    overall_accuracy: float
    xp: int

@router.get("/<string:student_username>", summary="Get student stats", response_model=StudentStatsResponse)
def get_student_stats(student_username, db: db_dependency, current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to see stats.",
        )
    
    student = (
        db.query(User).filter((User.username == student_username)).first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="No such user in database"
        )
    
    student_stat = (
        db.query(StudentStats).filter(StudentStats.user_id == student.id).first()
    )

    if not student_stat:
        raise HTTPException(
            status_code=404,
            detail="No avaliable stats for user."
        )
    
    
    result = StudentStatsResponse (
                student= student_username,
                total_attempts= student_stat.total_attempts,
                overall_accuracy= float(student_stat.overall_accuracy),
                xp= student_stat.xp,
            )

    return result


@router.get("/my-stats", summary="Get logged in student stats", response_model=StudentStatsResponse)
def get_my_stats(db: db_dependency, current_user: User = Depends(get_current_user)):
    
    
    student_stat = (
        db.query(StudentStats).filter(StudentStats.user_id == current_user.id).first()
    )

    if not student_stat:
        raise HTTPException(
            status_code=404,
            detail="No avaliable stats for user."
        )
    
    
    result = StudentStatsResponse (
                student= current_user.username,
                total_attempts= student_stat.total_attempts,
                overall_accuracy= float(student_stat.overall_accuracy),
                xp= student_stat.xp,
            )

    return result

