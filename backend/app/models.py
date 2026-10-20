# app/models.py
# Database tables, written as Python classes (SQLAlchemy 2.0 style).
# One class = one table. One Mapped[...] attribute = one column.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    # Always store time in UTC; convert to local time only when displaying
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))   # never the plain password
    role: Mapped[str] = mapped_column(String(20), default="student")  # "student" or "tutor"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="user")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    option_a: Mapped[str] = mapped_column(String(300))
    option_b: Mapped[str] = mapped_column(String(300))
    option_c: Mapped[str] = mapped_column(String(300))
    option_d: Mapped[str] = mapped_column(String(300))
    answer: Mapped[str] = mapped_column(String(1))            # "A", "B", "C" or "D"
    concept: Mapped[str] = mapped_column(String(100), index=True)
    difficulty: Mapped[int] = mapped_column(default=1)        # 1 easy, 2 medium, 3 hard

    def option_text(self, letter: str) -> str:
        """'B' -> the text of option B"""
        return {"A": self.option_a, "B": self.option_b,
                "C": self.option_c, "D": self.option_d}[letter]


class Attempt(Base):
    """One row every time a student answers a question. The core event table:
    every analytic in the app is computed from these rows."""
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    selected: Mapped[str] = mapped_column(String(1))
    is_correct: Mapped[bool]
    hint: Mapped[str | None] = mapped_column(Text, default=None)
    hint_source: Mapped[str | None] = mapped_column(String(20), default=None)  # "ai" or "fallback"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped["User"] = relationship(back_populates="attempts")
    question: Mapped["Question"] = relationship()


class ConceptGap(Base):
    """One row per (student, concept): how much that student struggles with it.
    score: 0.0 = mastered, 1.0 = struggling."""
    __tablename__ = "concept_gaps"
    # A student has at most ONE gap row per concept
    __table_args__ = (UniqueConstraint("user_id", "concept"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    concept: Mapped[str] = mapped_column(String(100))
    score: Mapped[float] = mapped_column(default=0.5)
    attempts: Mapped[int] = mapped_column(default=0)
    correct: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
