# app/schemas.py
# Pydantic schemas = the exact shape of data coming IN to and going OUT of the API.
# models.py describes the database; schemas.py describes the API contract.
# Keeping them separate means we never leak a column (like password_hash) by accident.

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    # bcrypt only uses the first 72 bytes of a password, so we cap the length
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    # from_attributes lets Pydantic read a SQLAlchemy object directly
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Questions ----------
class QuestionCreate(BaseModel):
    text: str = Field(min_length=5)
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    answer: str = Field(pattern="^[ABCD]$")
    concept: str = Field(min_length=2, max_length=100)
    difficulty: int = Field(default=1, ge=1, le=3)


class QuestionOut(BaseModel):
    """What a student sees. Note: NO 'answer' field."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    concept: str
    difficulty: int


class ConceptCount(BaseModel):
    concept: str
    questions: int


# ---------- Attempts ----------
class AttemptCreate(BaseModel):
    question_id: int
    selected: str = Field(pattern="^[ABCD]$")


class AttemptResult(BaseModel):
    attempt_id: int
    is_correct: bool
    correct_answer: str | None      # revealed only after a wrong answer
    concept: str
    gap_score: float
    hint: str | None                # only for wrong answers
    hint_source: str | None         # "ai" or "fallback"


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question_id: int
    selected: str
    is_correct: bool
    hint: str | None
    created_at: datetime


# ---------- Analytics ----------
class GapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    concept: str
    score: float
    attempts: int
    correct: int


class DashboardStats(BaseModel):
    total_students: int
    active_students_24h: int
    attempts_24h: int
    accuracy_24h: float          # percent, 0-100
    at_risk_students: int


class ConceptStat(BaseModel):
    concept: str
    attempts: int
    error_rate: float            # percent, 0-100
    avg_gap: float


class AtRiskStudent(BaseModel):
    student_id: int
    name: str
    concept: str
    gap_score: float
    attempts: int
