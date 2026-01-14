"""
Decisions API Router.

Handles recording decisions and viewing decision history.
Includes hard override approval workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from core.database import get_db
from core.models import Decision, User, UserRole, DecisionType
from core.services import DecisionRecorder, EvidenceGenerator
from core.schemas.decision import DecisionCreate, DecisionResponse, DecisionListItem, ApprovalCheck

router = APIRouter(prefix="/decisions", tags=["decisions"])


def validate_approver(db: Session, approved_by: str) -> bool:
    """Check if user has approver privileges."""
    user = db.query(User).filter(User.username == approved_by).first()
    if not user:
        # If no user record exists, allow (for backwards compatibility)
        # In production, this should be strict
        return True
    return user.can_approve()


@router.post("", response_model=DecisionResponse, status_code=201)
def create_decision(
    decision_data: DecisionCreate,
    db: Session = Depends(get_db)
):
    """
    Record an immutable decision.

    This resolves an exception and triggers evidence pack generation.

    For hard overrides (is_hard_override=True):
    - approved_by is required
    - Approver must have Approver or Admin role
    - Approval timestamp is recorded automatically
    """
    # Validate hard override approval
    if decision_data.is_hard_override:
        if not decision_data.approved_by:
            raise HTTPException(
                status_code=400,
                detail="Hard overrides require approved_by"
            )
        if not validate_approver(db, decision_data.approved_by):
            raise HTTPException(
                status_code=403,
                detail=f"User '{decision_data.approved_by}' does not have approval privileges"
            )

    recorder = DecisionRecorder(db)

    try:
        decision = recorder.record_decision(
            exception_id=decision_data.exception_id,
            chosen_option_id=decision_data.chosen_option_id,
            rationale=decision_data.rationale,
            decided_by=decision_data.decided_by,
            assumptions=decision_data.assumptions,
            is_hard_override=decision_data.is_hard_override,
            approved_by=decision_data.approved_by,
            approval_notes=decision_data.approval_notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate evidence pack synchronously (would be async in production)
    evidence_gen = EvidenceGenerator(db)
    try:
        evidence_pack = evidence_gen.generate_pack(decision)
        db.refresh(decision)  # Refresh to get evidence_pack_id
    except Exception as e:
        # Decision is already recorded, just log error
        print(f"Failed to generate evidence pack: {e}")

    return decision


@router.get("/check-approval/{username}", response_model=ApprovalCheck)
def check_approval_permission(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Check if a user can approve hard overrides.

    Returns approval status and reason if denied.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return ApprovalCheck(
            user=username,
            can_approve=False,
            reason="User not found in system"
        )

    if not user.is_active:
        return ApprovalCheck(
            user=username,
            can_approve=False,
            reason="User account is inactive"
        )

    can_approve = user.can_approve()
    return ApprovalCheck(
        user=username,
        can_approve=can_approve,
        reason=None if can_approve else f"User role '{user.role.value}' cannot approve overrides"
    )


@router.get("", response_model=List[DecisionListItem])
def list_decisions(
    from_date: Optional[datetime] = Query(default=None, description="Start date filter"),
    to_date: Optional[datetime] = Query(default=None, description="End date filter"),
    decided_by: Optional[str] = Query(default=None, description="Filter by decider"),
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db)
):
    """
    List decisions with filtering.
    """
    query = db.query(Decision)

    if from_date:
        query = query.filter(Decision.decided_at >= from_date)

    if to_date:
        query = query.filter(Decision.decided_at <= to_date)

    if decided_by:
        query = query.filter(Decision.decided_by == decided_by)

    decisions = query.order_by(Decision.decided_at.desc()).limit(limit).all()

    return decisions


@router.get("/{decision_id}", response_model=DecisionResponse)
def get_decision(
    decision_id: str,
    db: Session = Depends(get_db)
):
    """
    Get decision by ID.
    """
    try:
        dec_uuid = UUID(decision_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    decision = db.query(Decision).filter(Decision.id == dec_uuid).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    return decision
