"""
Evaluations API Router.

Handles triggering policy evaluations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from core.database import get_db
from core.models import Signal
from core.services import PolicyEngine, Evaluator, ExceptionEngine
from core.schemas.evaluation import EvaluationTrigger, EvaluationResponse

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("", response_model=List[EvaluationResponse])
def trigger_evaluation(
    trigger_data: EvaluationTrigger,
    db: Session = Depends(get_db)
):
    """
    Trigger policy evaluation for a pack.

    This evaluates all active policies against recent signals.
    """
    # Get active policies for pack
    policy_engine = PolicyEngine(db)
    policies = policy_engine.get_active_policies(trigger_data.pack)

    if not policies:
        raise HTTPException(
            status_code=404,
            detail=f"No active policies found for pack '{trigger_data.pack}'"
        )

    # Get recent signals for pack (last 24 hours)
    since = datetime.utcnow() - timedelta(hours=24)
    signals = (
        db.query(Signal)
        .filter(
            Signal.pack == trigger_data.pack,
            Signal.observed_at >= since
        )
        .order_by(Signal.observed_at.desc())
        .all()
    )

    if not signals:
        raise HTTPException(
            status_code=404,
            detail=f"No recent signals found for pack '{trigger_data.pack}'"
        )

    # Evaluate each policy
    evaluator = Evaluator(db)
    exception_engine = ExceptionEngine(db)
    evaluations = []

    for policy_version in policies:
        # Evaluate policy against signals
        evaluation = evaluator.evaluate(
            policy_version,
            signals,
            trigger_data.replay_namespace
        )
        evaluations.append(evaluation)

        # Generate exception if needed
        exception = exception_engine.generate_exception(evaluation, policy_version)
        if exception:
            # Exception was raised
            pass

    return evaluations


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get evaluation by ID.
    """
    from uuid import UUID
    from core.models import Evaluation

    try:
        eval_uuid = UUID(evaluation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_uuid).first()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return evaluation
