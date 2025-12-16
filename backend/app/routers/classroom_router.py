from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from ..routers.auth import get_current_user
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models.users import User
from ..models.classroom import Classroom
from ..models.user_classroom import user_classroom
import random

router = APIRouter(prefix="/classroom", tags=['classroom'])
db_dependency = Annotated[Session, Depends(get_db)]

class CreateClassroomRequest(BaseModel):
    
    classroom_name: str
    
def generateClasroomCode():
    sample_list = ['A', 'B', 'C', 'D']
    return random.shuffle(sample_list)


@router.post("/create", summary="Create new classroom")
def create_new_classroom(request: CreateClassroomRequest,
                        db: db_dependency,
                        current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="User does not have permission to create classrooms.")
    
    invalid_class_code  = True
    while invalid_class_code:
        new_class_code = generateClasroomCode()
        existing = db.query(Classroom).filter(Classroom.class_code == request.class_code).first() #vec postoji classroom sa tim kodom
        if existing is None:
            invalid_class_code = False

    new_classroom = Classroom(
        class_code=new_class_code,
        classroom_name = request.classroom_name,
        teacher_id = current_user.id
    )

    db.add(new_classroom)
    db.commit()
    db.refresh(new_classroom)

    #add users to many to many relationship
    query = user_classroom.insert().values(
        user_id=current_user.id,
        class_id=new_classroom.id
    )

    db.execute(query)
    db.commit()

    return {"message": "Classroom created", "classroom_code": new_classroom.class_code}

