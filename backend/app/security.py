# app/security.py
# Password hashing (bcrypt) and login tokens (JWT).

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"   # HMAC + SHA-256: one secret key both signs and verifies


def hash_password(plain: str) -> str:
    """bcrypt adds a random salt and is deliberately slow, so leaked hashes
    are very expensive to crack."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int, role: str) -> str:
    """A JWT is three base64 parts: header.payload.signature.
    The payload is READABLE by anyone, so never put secrets in it.
    The signature proves the server created it and nobody edited it."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError if the token is fake, edited or expired."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
