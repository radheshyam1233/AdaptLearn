# app/services/gap.py
# The "gap score": how much a student struggles with a concept.
#
# It is an exponential moving average (EMA) of mistakes:
#     new_score = (1 - ALPHA) * old_score + ALPHA * (1 if wrong else 0)
# - Recent answers count more than old ones, so an improving student's score falls.
# - It always stays between 0 (mastered) and 1 (struggling), with no clamping needed.
# - A brand-new concept starts at 0.5 ("we don't know yet").

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ConceptGap

ALPHA = 0.3            # how strongly the latest answer moves the score
START_SCORE = 0.5
AT_RISK = 0.7          # at or above this, the tutor is alerted


def next_score(old: float, is_correct: bool) -> float:
    """Pure function, so it is easy to unit-test."""
    mistake = 0.0 if is_correct else 1.0
    return round((1 - ALPHA) * old + ALPHA * mistake, 4)


def update_gap(db: Session, user_id: int, concept: str, is_correct: bool) -> ConceptGap:
    """Find (or create) the student's gap row for this concept and update it.
    The caller commits, so the attempt and the gap are saved together."""
    gap = db.scalar(
        select(ConceptGap).where(ConceptGap.user_id == user_id, ConceptGap.concept == concept)
    )
    if gap is None:
        gap = ConceptGap(user_id=user_id, concept=concept, score=START_SCORE, attempts=0, correct=0)
        db.add(gap)
    gap.score = next_score(gap.score, is_correct)
    gap.attempts += 1
    if is_correct:
        gap.correct += 1
    return gap
