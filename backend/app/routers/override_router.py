from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models.users import User
from ..routers.auth import get_current_user
from ..models.student_stats import StudentStats
from ..models.teacher_actions import TeacherAction
from ..models.recommendations import Recommendation
from pydantic import BaseModel

router = APIRouter(prefix="/override", tags=["stats"])
db_dependency = Annotated[Session, Depends(get_db)]


class OverrideRequest(BaseModel):
    student_username: str
    action: str

#PRETPOSTAVKA: uvijek overrideamo najnoviji recommendation
#TODO: provjeri mislimo li za svakog učenika spremati više recommendationa i trebamo li onda dodati created at u recommendation table
@router.post("/", summary="Override model recommendation")
def override_decision(request: OverrideRequest, db: db_dependency, current_user: User = Depends(get_current_user),):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to override recommendations.",
        )
    
    student = (
        db.query(User).filter((User.username == request.student_username)).first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="No such user in database"
        )

    #najnoviji recommendation za studenta
    recommendation = (
        db.query(Recommendation).filter((Recommendation.user_id == student.id)).order_by(Recommendation.created_at.desc()).first()
    )

    if not recommendation:
        raise HTTPException(
            status_code=404,
            detail="No recommendation for user in database"
        )

    new_override = TeacherAction(
        teacher_id=current_user.id,
        user_id = student.id,
        action = request.action,
        recommendation_id = recommendation.id 
    )

    db.add(new_override)
    db.commit()
    
    return {"message": "Action passed", "action": new_override.action}


