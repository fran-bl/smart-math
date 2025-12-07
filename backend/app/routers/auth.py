from datetime import timedelta, datetime, timezone
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

class CreateUserRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED,  summary="kreiranje usera")
async def create_user(db: db_dependency,
                      create_user_request: CreateUserRequest):
    print("TYPE:", type(create_user_request.password))
    print("VALUE:", create_user_request.password)
    print("LEN:", len(str(create_user_request.password)))

 #TODO: OVO POPRAVITI 
    create_user_model = User(
        username = create_user_request.username,
        password=pwd_context.hash(create_user_request.password),
        role='teacher',
        topic_id=None,
        class_code='ZG45'
    )
    db.add(create_user_model)
    db.commit()

  
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db:db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
    token = create_access_token(user.username, user.id, timedelta(minutes=45))

    return {'access_token': token, 'token_type': 'bearer'}

def authenticate_user(username: str, password: str, db):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not password == user.password: #pwd_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': str(user_id)}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)