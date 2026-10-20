# app/deps.py
# Reusable dependencies: "who is calling?" and "are they allowed?"

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

# Reads the "Authorization: Bearer <token>" header.
# tokenUrl makes the Authorize button in /docs work.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_from_token(token: str, db: Session) -> User | None:
    """Shared by HTTP routes and the WebSocket. Returns None if invalid."""
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
    return db.get(User, user_id)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    user = get_user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(*roles: str):
    """Role-based access control (RBAC).
    Usage: user: User = Depends(require_role("tutor"))
    401 = we don't know who you are. 403 = we know, but you're not allowed."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for your role")
        return user
    return checker
