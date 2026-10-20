# app/routers/questions.py
# Browse concepts, get the next question to practise, and (tutors) add questions.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_role
from ..models import Attempt, Question, User
from ..schemas import ConceptCount, QuestionCreate, QuestionOut

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("/concepts", response_model=list[ConceptCount])
def list_concepts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.execute(
        select(Question.concept, func.count(Question.id))
        .group_by(Question.concept)
        .order_by(Question.concept)
    ).all()
    return [ConceptCount(concept=c, questions=n) for c, n in rows]


@router.get("/next", response_model=QuestionOut)
def next_question(
    concept: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pick a question in this concept that the student has NOT yet answered
    correctly. If they've solved them all, pick any question in the concept."""
    solved = select(Attempt.question_id).where(
        Attempt.user_id == user.id, Attempt.is_correct.is_(True)
    )
    base = select(Question).where(Question.concept == concept)
    q = db.scalar(base.where(Question.id.not_in(solved)).order_by(func.random()).limit(1))
    if q is None:
        q = db.scalar(base.order_by(func.random()).limit(1))
    if q is None:
        raise HTTPException(status_code=404, detail="No questions for this concept")
    return q


@router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def create_question(
    data: QuestionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("tutor")),
):
    q = Question(**data.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return q
