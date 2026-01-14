"""
Stats API Router.

Provides dashboard statistics for the UI.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Optional

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

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(
    pack: Optional[str] = Query(None, description="Filter by pack (treasury, wealth)"),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics.

    Returns counts for exceptions, decisions, signals, and policies.
    """
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # Exception stats - join through Evaluation -> PolicyVersion -> Policy for pack filter
    exception_query = db.query(ExceptionModel)
    if pack:
        exception_query = (
            exception_query
            .join(ExceptionModel.evaluation)
            .join(Evaluation.policy_version)
            .join(PolicyVersion.policy)
            .filter(Policy.pack == pack)
        )

    open_exceptions = exception_query.filter(ExceptionModel.status == ExceptionStatus.OPEN).count()

    # Count by severity (only open exceptions)
    severity_counts = {}
    for severity in ExceptionSeverity:
        severity_query = db.query(ExceptionModel).filter(
            ExceptionModel.status == ExceptionStatus.OPEN,
            ExceptionModel.severity == severity
        )
        if pack:
            severity_query = (
                severity_query
                .join(ExceptionModel.evaluation)
                .join(Evaluation.policy_version)
                .join(PolicyVersion.policy)
                .filter(Policy.pack == pack)
            )
        severity_counts[severity.value] = severity_query.count()

    # Decision stats - join through Exception -> Evaluation -> PolicyVersion -> Policy
    decision_query = db.query(Decision)
    if pack:
        decision_query = (
            decision_query
            .join(Decision.exception)
            .join(ExceptionModel.evaluation)
            .join(Evaluation.policy_version)
            .join(PolicyVersion.policy)
            .filter(Policy.pack == pack)
        )

    total_decisions = decision_query.count()

    recent_decision_query = db.query(Decision).filter(Decision.decided_at >= last_24h)
    if pack:
        recent_decision_query = (
            recent_decision_query
            .join(Decision.exception)
            .join(ExceptionModel.evaluation)
            .join(Evaluation.policy_version)
            .join(PolicyVersion.policy)
            .filter(Policy.pack == pack)
        )
    recent_decisions = recent_decision_query.count()

    # Signal stats - direct pack field
    signal_query = db.query(Signal)
    if pack:
        signal_query = signal_query.filter(Signal.pack == pack)
    total_signals = signal_query.count()

    recent_signal_query = db.query(Signal).filter(Signal.observed_at >= last_24h)
    if pack:
        recent_signal_query = recent_signal_query.filter(Signal.pack == pack)
    recent_signals = recent_signal_query.count()

    # Policy stats - direct pack field
    policy_query = db.query(Policy)
    if pack:
        policy_query = policy_query.filter(Policy.pack == pack)
    total_policies = policy_query.count()

    # Active policies (have an active version)
    active_policies_query = db.query(func.count(func.distinct(PolicyVersion.policy_id))).filter(
        PolicyVersion.status == PolicyStatus.ACTIVE
    )
    if pack:
        active_policies_query = active_policies_query.join(Policy).filter(Policy.pack == pack)
    active_policies = active_policies_query.scalar() or 0

    return {
        "pack": pack or "all",
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
