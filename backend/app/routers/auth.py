from datetime import timedelta, datetime, timezone
from enum import Enum
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from ..db import get_db
from ..models.users import User
from ..models.user_classroom import user_classroom
from ..models.classroom import Classroom
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from ..config import settings


router = APIRouter(prefix="/auth", tags=['auth'])

SECRET_KEY= settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='/auth/my-token')

class RoleEnum(str, Enum):
    teacher = "teacher"
    student = "student"

class CreateUserRequest(BaseModel):
    username: str
    password: str | None = None
    role: RoleEnum

class Token(BaseModel):
    access_token: str
    token_type: str

class MyLoginForm(BaseModel):
    username: str
    password: str | None = None
    class_code: str | None = None


db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED,  summary="kreiranje usera")
async def create_user(db: db_dependency,
                      create_user_request: CreateUserRequest):

    print(db.query(User).all())


    create_user_model = User(
        username = create_user_request.username,
        password = create_user_request.password or None, # TODO: ako hashiramo lozinku u bazi -> password=pwd_context.hash(create_user_request.password),
        role= create_user_request.role,
       
    )
    db.add(create_user_model)
    db.commit()
    print(db.get_bind())


  
@router.post("/token", response_model=Token, summary="classic login - not used")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db:db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    token = create_access_token(user.username, user.id, timedelta(minutes=45))

    return {'access_token': token, 'token_type': 'bearer'}



@router.post("/my-token", response_model=Token, summary="login for students and teachers separated")
async def login_for_access_token(form_data: MyLoginForm,
                                 db:db_dependency):
    #ako nema passworda znaci da je ucenik
    if not form_data.password:
        user = authenticate_student(form_data.username, form_data.class_code, db)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    
    else: #password postoji -> login za profesora
        user = authenticate_user(form_data.username, form_data.password, db)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    
    token = create_access_token(user.username, user.id, timedelta(minutes=50))
    return {'access_token': token, 'token_type': 'bearer'}



def authenticate_student(username: str, class_code: str, db):
    # korisnik
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False

    # dohvati classroom sa dobivenim class_codeom
    classroom = db.query(Classroom).filter(Classroom.class_code == class_code).first()
    if not classroom:
        return False

    # Provjeri postoji li kombinacija user_id i class_id u user_classroom
    association = db.query(user_classroom).filter(
        user_classroom.c.user_id == user.id,
        user_classroom.c.class_id == classroom.id
    ).first()

    if not association:
        return False

    return user


#koristi se za autentifikaciju nastavnika
def authenticate_user(username: str, password: str, db):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not password == user.password: #pwd_context.verify(password, user.hashed_password): #provjeri je li dobar password
        return False
    return user


def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': str(user_id)}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)



def get_current_user(token: str = Depends(oauth2_bearer), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user



@router.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
    }