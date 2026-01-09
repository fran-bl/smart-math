from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..db import get_db
from ..models.classroom import Classroom
from ..models.recommendations import Recommendation
from ..models.rounds import Round
from ..models.teacher_actions import TeacherAction
from ..models.user_classroom import user_classroom
from ..models.users import User
from ..routers.auth import get_current_user

router = APIRouter(prefix="/override", tags=["override"])
db_dependency = Annotated[Session, Depends(get_db)]


class OverrideRequest(BaseModel):
    student_username: str
    action: str


class RecommendationResponse(BaseModel):
    student: str
    current_difficulty: int
    last_recommendation: Optional[str]
    confidence: Optional[float]


# PRETPOSTAVKA: uvijek overrideamo najnoviji recommendation
@router.post("/", summary="Override model recommendation")
def override_decision(
    request: OverrideRequest,
    db: db_dependency,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=403,
            detail="User does not have permission to override recommendations.",
        )

    student = db.query(User).filter((User.username == request.student_username)).first()

    if not student:
        raise HTTPException(status_code=404, detail="No such user in database")

    is_my_student = (
        db.query(Classroom.id)
        .join(user_classroom, user_classroom.c.class_id == Classroom.id)
        .filter(
            Classroom.teacher_id == current_user.id,
            user_classroom.c.user_id == student.id,
        )
        .first()
        is not None
    )
    if not is_my_student:
        raise HTTPException(
            status_code=403, detail="You are not teacher of this student."
        )

    # najnoviji recommendation za studenta
    recommendation = (
        db.query(Recommendation)
        .outerjoin(Round, Round.id == Recommendation.round_id)
        .filter(Recommendation.user_id == student.id)
        .order_by(desc(Round.end_ts).nulls_last(), desc(Recommendation.id))
        .first()
    )

    if not recommendation:
        raise HTTPException(
            status_code=404, detail="No recommendation for user in database"
        )

    # prvo promijeni težinu učeniku

    if request.action == "override_up":
        if student.current_difficulty < 5:
            student.current_difficulty += 1
    elif request.action == "override_down":
        if student.current_difficulty > 1:
            student.current_difficulty -= 1
    elif request.action == "accept":
        pass
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    db.add(student)

    # zabiljezi promjenu u sustavu
    new_override = TeacherAction(
        teacher_id=current_user.id,
        user_id=student.id,
        action=request.action,
        recommendation_id=recommendation.id,
    )

    db.add(new_override)
    db.commit()

    return {"message": "Action passed", "action": new_override.action}


@router.get(
    "/recommendations/{classroom_name}",
    response_model=list[RecommendationResponse],
    summary="Fetch latest recommendations for every student in a classroom",
)
def fetch_recommendations(
    classroom_name,
    db: db_dependency,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=403, detail="Only teachers can view recommendations."
        )

    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.class_name == classroom_name,
            Classroom.teacher_id == current_user.id,
        )
        .first()
    )
    if not classroom:
        raise HTTPException(status_code=404, detail="No such classroom.")

    students = (
        db.query(User)
        .join(user_classroom, user_classroom.c.user_id == User.id)
        .filter(
            user_classroom.c.class_id == classroom.id,
            User.role == "student",
        )
        .order_by(User.username.asc())
        .all()
    )

    result = []
    for student in students:
        # query se moze optimizirati
        recommendation = (
            db.query(Recommendation)
            .outerjoin(Round, Round.id == Recommendation.round_id)
            .filter(Recommendation.user_id == student.id)
            .order_by(desc(Round.end_ts).nulls_last(), desc(Recommendation.id))
            .first()
        )
        student_response = RecommendationResponse(
            student=student.username,
            current_difficulty=student.current_difficulty,
            last_recommendation=recommendation.rec if recommendation else None,
            confidence=float(recommendation.confidence) if recommendation else None,
        )
        result.append(student_response)

    return result
