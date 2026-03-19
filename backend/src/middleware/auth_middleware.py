import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.config import get_settings
from src.middleware.error_handler import AuthenticationError
from src.models.database import get_db
from src.models.user import User

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 30


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ")
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Invalid token payload")
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise AuthenticationError("Invalid or expired token")

    user = db.get(User, user_id)
    if not user:
        raise AuthenticationError("User not found")

    return user
