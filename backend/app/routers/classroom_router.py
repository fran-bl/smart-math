from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from ..routers.auth import get_current_user
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models.users import User
from ..models.classroom import Classroom
from ..models.user_classroom import user_classroom

router = APIRouter(prefix="/classroom", tags=['classroom'])
db_dependency = Annotated[Session, Depends(get_db)]

class CreateClassroomRequest(BaseModel):
    class_code: str
    classroom_name: str
    


@router.post("/create", summary="Create new classroom")
def create_new_classroom(request: CreateClassroomRequest,
                        db: db_dependency,
                        current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="User does not have permission to create classrooms.")
    
    existing = db.query(Classroom).filter(Classroom.class_code == request.class_code).first() #vec postoji classroom sa tim kodom
    if existing:
        raise HTTPException(status_code=400, detail="Classroom with that class_code already exists.")

    new_classroom = Classroom(
        class_code=request.class_code,
        classroom_name = request.classroom_name,
        teacher_id = current_user.id
    )

    db.add(new_classroom)
    db.commit()
    db.refresh(new_classroom)

    query = user_classroom.insert().values(
        user_id=current_user.id,
        class_id=new_classroom.id
    )

    db.execute(query)
    db.commit()

    return {"message": "Classroom created", "classroom_id": new_classroom.id}

