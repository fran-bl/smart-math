import datetime
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models.users import User
from ..routers.auth import get_current_user
from ..models.student_stats import StudentStats
from ..models.teacher_actions import TeacherAction
from ..models.recommendations import Recommendation
from ..models.classroom import Classroom
from ..models.user_classroom import user_classroom
from pydantic import BaseModel
from typing import Optional
router = APIRouter(prefix="/actions", tags=["actions"])
db_dependency = Annotated[Session, Depends(get_db)]

class TeacherActionResponse(BaseModel):
    student_username: str
    action: str
    recommendation_id: UUID
    model_recommendation: str
    model_confidence: float
    created_at: datetime

@router.get("/", response_model=list[TeacherActionResponse], summary="Fetch all actions of logged in teacher")
def fetch_recommendations( db: db_dependency, current_user: User = Depends(get_current_user),):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=403, detail="Only teachers can view their actions."
        )

    actions = (
        db.query(TeacherAction).filter(TeacherAction.teacher_id == current_user.id).all()
    )

    if not actions :
        raise HTTPException(status_code=404, detail="User does not have any actions to show.")
     
    result = []
    for action in actions:
        student  = (
        db.query(User)
        .filter(
            User.id == action.user_id,
            User.role == "student",
        )
        
        .first()
    )
        recomm = (db.query(Recommendation).filter(Recommendation.id == action.recommendation_id).first())

        teacher_act = TeacherActionResponse (
            student_username = student.username,
            action = action.action,
            recommendation_id =  action.recommendation_id,
            model_recommendation = recomm.rec,
            model_confidence = recomm.confidence,
            created_at = action.created_at
        )

        result.append(teacher_act)

    return result

