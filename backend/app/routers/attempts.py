# app/routers/attempts.py
# The core flow: a student submits an answer.

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import Attempt, Question, User
from ..schemas import AttemptCreate, AttemptOut, AttemptResult
from ..services.ai import generate_hint
from ..services.cache import DASHBOARD_KEYS, cache_delete
from ..services.gap import update_gap
from ..services.realtime import manager

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("", response_model=AttemptResult, status_code=status.HTTP_201_CREATED)
def submit_attempt(
    data: AttemptCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("student")),
):
    # This is a normal "def" (not async), so FastAPI runs it in a worker thread:
    # the slow OpenAI call below doesn't block other requests.
    q = db.get(Question, data.question_id)
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    is_correct = data.selected == q.answer

    # 1. A hint only for wrong answers (AI, or a safe fallback)
    hint, hint_source = (None, None) if is_correct else generate_hint(q, data.selected)

    # 2. Save the attempt and update the gap score in ONE transaction:
    #    either both are saved or neither is.
    attempt = Attempt(user_id=user.id, question_id=q.id, selected=data.selected,
                      is_correct=is_correct, hint=hint, hint_source=hint_source)
    db.add(attempt)
    gap = update_gap(db, user.id, q.concept, is_correct)
    db.commit()

    # 3. Dashboard numbers changed -> drop the cached copies
    cache_delete(*DASHBOARD_KEYS)

    # 4. Tell connected tutors. BackgroundTasks runs this AFTER the response is
    #    sent, so the student never waits for the broadcast.
    background.add_task(manager.broadcast, {
        "type": "attempt",
        "student": user.name,
        "concept": q.concept,
        "is_correct": is_correct,
        "gap_score": round(gap.score, 2),
        "at": datetime.now(timezone.utc).isoformat(),
    })

    return AttemptResult(
        attempt_id=attempt.id,
        is_correct=is_correct,
        correct_answer=None if is_correct else q.answer,
        concept=q.concept,
        gap_score=round(gap.score, 2),
        hint=hint,
        hint_source=hint_source,
    )


@router.get("/me", response_model=list[AttemptOut])
def my_attempts(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("student")),
):
    limit = max(1, min(limit, 100))   # never let a client ask for a million rows
    return db.scalars(
        select(Attempt).where(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc()).limit(limit)
    ).all()
