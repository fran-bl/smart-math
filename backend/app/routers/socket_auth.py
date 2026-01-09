from jose import JWTError, jwt

from ..config import settings
from ..db import SessionLocal
from ..models.users import User


async def authenticate_socket_with_token(token: str):
    """Authenticate socket connection using JWT token."""
    if not token:
        return None
    token = token.strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("id")
        if not user_id:
            return None
    except JWTError:
        return None

    db = SessionLocal()
    return db.query(User).filter(User.id == user_id).first()
