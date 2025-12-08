from datetime import timedelta, datetime, timezone
from enum import Enum
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from ..db import get_db
from ..models.users import User
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from ..config import settings


router = APIRouter(prefix="/auth", tags=['auth'])

SECRET_KEY= settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

class RoleEnum(str, Enum):
    teacher = "teacher"
    student = "student"

class CreateUserRequest(BaseModel):
    username: str
    password: str | None = None
    class_code: str
    role: RoleEnum

class Token(BaseModel):
    access_token: str
    token_type: str

class MyLoginForm(BaseModel):
    username: str
    password: str | None = None
    class_code: str


db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED,  summary="kreiranje usera")
async def create_user(db: db_dependency,
                      create_user_request: CreateUserRequest):

    print(db.query(User).all())


    create_user_model = User(
        username = create_user_request.username,
        password = create_user_request.password or None, # TODO: ako hashiramo lozinku u bazi -> password=pwd_context.hash(create_user_request.password),
        role= create_user_request.role,
        class_code= create_user_request.class_code
    )
    db.add(create_user_model)
    db.commit()
    print(db.get_bind())


  
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db:db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    token = create_access_token(user.username, user.id, timedelta(minutes=45))

    return {'access_token': token, 'token_type': 'bearer'}



@router.post("/my-token", response_model=Token)
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
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not class_code == user.class_code: #provjeri je li dobar classcode
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