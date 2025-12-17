from typing import Annotated, List
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

class AddStudentsReqest(BaseModel):
    classroom_name: str
    student_list: List[str]

    
def generateClasroomCode():
    letters = 'ABCD'

    code = ''.join(random.choice(letters) for _ in range(4))
    return code


@router.post("/create", summary="Create new classroom")
def create_new_classroom(request: CreateClassroomRequest,
                        db: db_dependency,
                        current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="User does not have permission to create classrooms.")
    
    invalid_class_code  = True
    new_class_code = None
    while invalid_class_code:
        new_class_code = generateClasroomCode()
        existing = db.query(Classroom).filter(Classroom.class_code == new_class_code).first() #vec postoji classroom sa tim kodom
        if existing is None:
            invalid_class_code = False
    print(new_class_code)
    new_classroom = Classroom(
        class_code=new_class_code,
        class_name = request.classroom_name,
        teacher_id = current_user.id
    )

    db.add(new_classroom)
    db.commit()
    db.refresh(new_classroom)

    #add teacher to many to many relationship
    query = user_classroom.insert().values(
        user_id=current_user.id,
        class_id=new_classroom.id
    )

    db.execute(query)
    db.commit()

    return {"message": "Classroom created", "classroom_code": new_classroom.class_code}

@router.post("/add-students", summary="adds students to already existing classroom")
def addStudents(request: AddStudentsReqest,
                        db: db_dependency,
                        current_user: User = Depends(get_current_user)):
    
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="User does not have permission to edit classrooms.")
    
    classroom = db.query(Classroom).filter((Classroom.class_name == request.classroom_name), (Classroom.teacher_id == current_user.id)).first()
    
    students = (
        db.query(User)
        .filter(User.username.in_(request.student_list))
        .all()
    )

    existing_user_ids = {
        row.user_id
        for row in db.execute(
            user_classroom.select().where(
                user_classroom.c.class_id == classroom.id,
                user_classroom.c.user_id.in_([s.id for s in students]) #uzima id svakog studenta u listi studenata
            )
        )
    }

    new_students = [
        s for s in students  #uzima studenta iz dobivene liste studenata 
        if s.id not in existing_user_ids #AKO oni vec nisu u razredu
    ]


    rows = [
        {
            "user_id": student.id,
            "class_id": classroom.id
        }
        for student in new_students
    ]

    db.execute(user_classroom.insert(), rows)
    db.commit()

    return {"message": "Students added"}




        
