"""
Exceptions API Router.

Handles listing and retrieving exceptions (for decision UI).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import case
from typing import List, Optional
from uuid import UUID

from core.database import get_db
from core.models import Exception, ExceptionStatus, ExceptionSeverity
from core.schemas.exception import ExceptionListItem, ExceptionDetail
from core.api.dependencies import get_required_pack, validate_pack

router = APIRouter(prefix="/exceptions", tags=["exceptions"])

# SQL severity ordering: critical (0) > high (1) > medium (2) > low (3)
SEVERITY_ORDER = case(
    (Exception.severity == ExceptionSeverity.CRITICAL, 0),
    (Exception.severity == ExceptionSeverity.HIGH, 1),
    (Exception.severity == ExceptionSeverity.MEDIUM, 2),
    (Exception.severity == ExceptionSeverity.LOW, 3),
    else_=4
)


@router.get("", response_model=List[ExceptionListItem])
def list_exceptions(
    pack: str = Depends(get_required_pack),
    status: Optional[str] = Query(default="open", description="Filter by status: open, resolved, dismissed"),
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db)
):
    """
    List exceptions with filtering.

    Pack is required to enforce pack isolation.
    Returns exceptions sorted by severity (descending) then raised_at (descending).
    Sorting is done in SQL using CASE expression for efficiency.
    """
    query = db.query(Exception)

    # Filter by status
    if status:
        status_map = {
            "open": ExceptionStatus.OPEN,
            "resolved": ExceptionStatus.RESOLVED,
            "dismissed": ExceptionStatus.DISMISSED
        }
        status_enum = status_map.get(status.lower())
        if status_enum:
            query = query.filter(Exception.status == status_enum)

    # Filter by pack (join through evaluation -> policy_version -> policy)
    from core.models import Evaluation, PolicyVersion, Policy
    query = (
        query.join(Exception.evaluation)
        .join(Evaluation.policy_version)
        .join(PolicyVersion.policy)
        .filter(Policy.pack == pack)
    )

    # Order by severity (critical > high > medium > low) then timestamp using SQL CASE
    exceptions = (
        query
        .order_by(SEVERITY_ORDER.asc(), Exception.raised_at.desc())
        .limit(limit)
        .all()
    )

    return exceptions


@router.get("/{exception_id}", response_model=ExceptionDetail)
def get_exception(
    exception_id: str,
    db: Session = Depends(get_db)
):
    """
    Get full exception detail for decision UI.

    This is the primary data source for the one-screen decision interface.
    Returns exception with related evaluation, policy, and signals.
    """
    from core.models import Evaluation, PolicyVersion, Policy, Signal
    from core.schemas.exception import EvaluationSummary, PolicySummary, SignalSummary

    try:
        exc_uuid = UUID(exception_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    exception = db.query(Exception).filter(Exception.id == exc_uuid).first()

    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Fetch related evaluation
    evaluation = exception.evaluation
    evaluation_summary = None
    if evaluation:
        evaluation_summary = EvaluationSummary(
            id=evaluation.id,
            result=evaluation.result.value,
            details=evaluation.details,
            evaluated_at=evaluation.evaluated_at,
            input_hash=evaluation.input_hash
        )

    # Fetch related policy through evaluation -> policy_version -> policy
    policy_summary = None
    if evaluation and evaluation.policy_version:
        policy_version = evaluation.policy_version
        policy = policy_version.policy
        policy_summary = PolicySummary(
            id=policy.id,
            name=policy.name,
            pack=policy.pack,
            description=policy.description,
            version_number=policy_version.version_number,
            rule_type=policy_version.rule_definition.get("type") if policy_version.rule_definition else None
        )

    # Fetch related signals
    signals_summary = []
    if evaluation and evaluation.signal_ids:
        signals = db.query(Signal).filter(Signal.id.in_(evaluation.signal_ids)).all()
        signals_summary = [
            SignalSummary(
                id=signal.id,
                signal_type=signal.signal_type,
                payload=signal.payload,
                source=signal.source,
                reliability=signal.reliability.value,
                observed_at=signal.observed_at
            )
            for signal in signals
        ]

    # Build response with related data
    return ExceptionDetail(
        id=exception.id,
        evaluation_id=exception.evaluation_id,
        fingerprint=exception.fingerprint,
        severity=exception.severity.value,
        status=exception.status.value,
        title=exception.title,
        context=exception.context,
        options=exception.options,
        raised_at=exception.raised_at,
        resolved_at=exception.resolved_at,
        evaluation=evaluation_summary,
        policy=policy_summary,
        signals=signals_summary
    )
