# app/routers/analytics.py
# Numbers for the student progress page and the tutor dashboard.

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, distinct, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_role
from ..models import Attempt, ConceptGap, Question, User
from ..schemas import AtRiskStudent, ConceptStat, DashboardStats, GapOut
from ..services.cache import cache_get, cache_set
from ..services.gap import AT_RISK

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------- Student ----------
@router.get("/me/gaps", response_model=list[GapOut])
def my_gaps(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    """The student's own gap per concept, weakest first."""
    return db.scalars(
        select(ConceptGap).where(ConceptGap.user_id == user.id).order_by(ConceptGap.score.desc())
    ).all()


# ---------- Tutor ----------
@router.get("/dashboard", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), _: User = Depends(require_role("tutor"))):
    # Cache-aside: 1) try Redis
    cached = cache_get("dashboard:stats")
    if cached is not None:
        return cached

    # 2) Cache miss: compute from PostgreSQL
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    total_students = db.scalar(select(func.count(User.id)).where(User.role == "student"))
    active, attempts, correct = db.execute(
        select(
            func.count(distinct(Attempt.user_id)),
            func.count(Attempt.id),
            # SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
            func.coalesce(func.sum(case((Attempt.is_correct, 1), else_=0)), 0),
        ).where(Attempt.created_at >= since)
    ).one()
    at_risk = db.scalar(
        select(func.count(distinct(ConceptGap.user_id))).where(ConceptGap.score >= AT_RISK)
    )
    stats = DashboardStats(
        total_students=total_students or 0,
        active_students_24h=active,
        attempts_24h=attempts,
        accuracy_24h=round(100 * correct / attempts, 1) if attempts else 0.0,
        at_risk_students=at_risk or 0,
    )

    # 3) Store for next time (TTL from settings, 30 s by default)
    cache_set("dashboard:stats", stats.model_dump())
    return stats


@router.get("/concepts", response_model=list[ConceptStat])
def concept_heatmap(db: Session = Depends(get_db), _: User = Depends(require_role("tutor"))):
    """Error rate per concept across all students: the heatmap."""
    cached = cache_get("dashboard:concepts")
    if cached is not None:
        return cached

    attempt_rows = db.execute(
        select(
            Question.concept,
            func.count(Attempt.id),
            func.sum(case((Attempt.is_correct, 0), else_=1)),   # number wrong
        )
        .join(Attempt, Attempt.question_id == Question.id)
        .group_by(Question.concept)
    ).all()
    avg_gap = dict(db.execute(
        select(ConceptGap.concept, func.avg(ConceptGap.score)).group_by(ConceptGap.concept)
    ).all())

    result = [
        ConceptStat(
            concept=concept,
            attempts=total,
            error_rate=round(100 * wrong / total, 1),
            avg_gap=round(float(avg_gap.get(concept, 0)), 2),
        )
        for concept, total, wrong in attempt_rows
    ]
    result.sort(key=lambda r: r.error_rate, reverse=True)   # worst first

    cache_set("dashboard:concepts", [r.model_dump() for r in result])
    return result


@router.get("/at-risk", response_model=list[AtRiskStudent])
def at_risk(db: Session = Depends(get_db), _: User = Depends(require_role("tutor"))):
    """Students with a gap score at or above the alert threshold."""
    rows = db.execute(
        select(User.id, User.name, ConceptGap.concept, ConceptGap.score, ConceptGap.attempts)
        .join(ConceptGap, ConceptGap.user_id == User.id)
        .where(ConceptGap.score >= AT_RISK)
        .order_by(ConceptGap.score.desc())
        .limit(20)
    ).all()
    return [
        AtRiskStudent(student_id=i, name=n, concept=c, gap_score=round(s, 2), attempts=a)
        for i, n, c, s, a in rows
    ]
