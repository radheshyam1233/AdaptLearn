# app/routers/auth.py
# Register, login, and "who am I?"

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import Token, UserCreate, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        # 409 Conflict: the resource already exists
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    # Public sign-up ALWAYS creates a student. Tutor accounts are created by an
    # admin script, so nobody can make themselves a tutor through the API.
    user = User(name=data.name, email=email, password_hash=hash_password(data.password), role="student")
    db.add(user)
    db.commit()
    db.refresh(user)   # reload to get the id the database assigned
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 forms call the field "username"; we use it for the email
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    # Same error for "no such user" and "wrong password", so attackers
    # can't find out which emails are registered
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_access_token(user.id, user.role)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
