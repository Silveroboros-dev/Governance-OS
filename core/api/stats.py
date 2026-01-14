"""
Stats API Router.

Provides dashboard statistics for the UI.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from core.database import get_db
from core.models import (
    Signal,
    Policy,
    PolicyVersion,
    PolicyStatus,
    Evaluation,
    Exception as ExceptionModel,
    ExceptionStatus,
    ExceptionSeverity,
    Decision,
)
from core.api.dependencies import get_required_pack

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(
    pack: str = Depends(get_required_pack),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics.

    Pack is required to enforce pack isolation.
    Returns counts for exceptions, decisions, signals, and policies.
    """
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # Exception stats - join through Evaluation -> PolicyVersion -> Policy for pack filter
    exception_query = (
        db.query(ExceptionModel)
        .join(ExceptionModel.evaluation)
        .join(Evaluation.policy_version)
        .join(PolicyVersion.policy)
        .filter(Policy.pack == pack)
    )

    open_exceptions = exception_query.filter(ExceptionModel.status == ExceptionStatus.OPEN).count()

    # Count by severity (only open exceptions)
    severity_counts = {}
    for severity in ExceptionSeverity:
        severity_query = (
            db.query(ExceptionModel)
            .filter(
                ExceptionModel.status == ExceptionStatus.OPEN,
                ExceptionModel.severity == severity
            )
            .join(ExceptionModel.evaluation)
            .join(Evaluation.policy_version)
            .join(PolicyVersion.policy)
            .filter(Policy.pack == pack)
        )
        severity_counts[severity.value] = severity_query.count()

    # Decision stats - join through Exception -> Evaluation -> PolicyVersion -> Policy
    decision_query = (
        db.query(Decision)
        .join(Decision.exception)
        .join(ExceptionModel.evaluation)
        .join(Evaluation.policy_version)
        .join(PolicyVersion.policy)
        .filter(Policy.pack == pack)
    )
    total_decisions = decision_query.count()

    recent_decision_query = (
        db.query(Decision)
        .filter(Decision.decided_at >= last_24h)
        .join(Decision.exception)
        .join(ExceptionModel.evaluation)
        .join(Evaluation.policy_version)
        .join(PolicyVersion.policy)
        .filter(Policy.pack == pack)
    )
    recent_decisions = recent_decision_query.count()

    # Signal stats - direct pack field
    signal_query = db.query(Signal).filter(Signal.pack == pack)
    total_signals = signal_query.count()

    recent_signal_query = db.query(Signal).filter(
        Signal.observed_at >= last_24h,
        Signal.pack == pack
    )
    recent_signals = recent_signal_query.count()

    # Policy stats - direct pack field
    policy_query = db.query(Policy).filter(Policy.pack == pack)
    total_policies = policy_query.count()

    # Active policies (have an active version)
    active_policies_query = (
        db.query(func.count(func.distinct(PolicyVersion.policy_id)))
        .filter(PolicyVersion.status == PolicyStatus.ACTIVE)
        .join(Policy)
        .filter(Policy.pack == pack)
    )
    active_policies = active_policies_query.scalar() or 0

    return {
        "pack": pack,
        "exceptions": {
            "open": open_exceptions,
            "by_severity": severity_counts,
        },
        "decisions": {
            "total": total_decisions,
            "last_24h": recent_decisions,
        },
        "signals": {
            "total": total_signals,
            "last_24h": recent_signals,
        },
        "policies": {
            "total": total_policies,
            "active": active_policies,
        },
    }
