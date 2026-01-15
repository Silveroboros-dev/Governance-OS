"""
Approvals API Router.

Sprint 3: Endpoints for managing agent-proposed actions requiring human review.

Safety invariants:
- All writes create pending_approval records
- Every approval/rejection logged to AuditEvent
- Approval UI shows full agent reasoning
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID

from core.database import get_db
from core.models import (
    ApprovalQueue, ApprovalActionType, ApprovalStatus,
    AuditEvent, AuditEventType,
    Signal, SignalReliability
)
from core.models.signal import compute_signal_content_hash
from core.schemas.approval import (
    ApprovalCreate, ApprovalResponse, ApprovalListResponse,
    ApprovalApproveRequest, ApprovalRejectRequest
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List approval queue entries with filtering and pagination.

    Returns pending items first, ordered by proposed_at descending.
    """
    query = db.query(ApprovalQueue)

    # Apply filters
    if status:
        try:
            status_enum = ApprovalStatus(status)
            query = query.filter(ApprovalQueue.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: pending, approved, rejected"
            )

    if action_type:
        try:
            action_enum = ApprovalActionType(action_type)
            query = query.filter(ApprovalQueue.action_type == action_enum)
        except ValueError:
            valid_types = ", ".join([t.value for t in ApprovalActionType])
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action_type: {action_type}. Valid values: {valid_types}"
            )

    # Get total count
    total = query.count()

    # Order by status (pending first) then by proposed_at descending
    query = query.order_by(
        # Pending items first
        func.case(
            (ApprovalQueue.status == ApprovalStatus.PENDING, 0),
            else_=1
        ),
        ApprovalQueue.proposed_at.desc()
    )

    # Paginate
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return ApprovalListResponse(
        items=[_approval_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific approval queue entry."""
    approval = db.query(ApprovalQueue).filter(ApprovalQueue.id == approval_id).first()

    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")

    return _approval_to_response(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
def approve_approval(
    approval_id: UUID,
    request: ApprovalApproveRequest,
    reviewed_by: str = Query(..., description="User approving the action"),
    db: Session = Depends(get_db)
):
    """
    Approve an agent-proposed action.

    This executes the proposed action and creates the corresponding entity.
    An audit event is logged for traceability.
    """
    approval = db.query(ApprovalQueue).filter(ApprovalQueue.id == approval_id).first()

    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Approval already {approval.status.value}"
        )

    # Execute the approved action based on type
    result_id = None

    if approval.action_type == ApprovalActionType.SIGNAL:
        result_id = _execute_signal_approval(approval, db)
    elif approval.action_type == ApprovalActionType.CONTEXT:
        # Context additions are additive-only, no separate entity created
        _execute_context_approval(approval, db)
    elif approval.action_type == ApprovalActionType.DISMISS:
        _execute_dismiss_approval(approval, db)
    elif approval.action_type == ApprovalActionType.POLICY_DRAFT:
        result_id = _execute_policy_draft_approval(approval, db)
    # Decision type requires special handling (human must still make the decision)

    # Mark as approved
    approval.approve(reviewed_by=reviewed_by, result_id=result_id, notes=request.notes)

    # Create audit event
    audit_event = AuditEvent(
        event_type=AuditEventType.DECISION_RECORDED,  # Using existing type
        aggregate_type="approval",
        aggregate_id=approval.id,
        event_data={
            "action": "approved",
            "action_type": approval.action_type.value,
            "proposed_by": approval.proposed_by,
            "result_id": str(result_id) if result_id else None,
            "notes": request.notes
        },
        actor=reviewed_by
    )
    db.add(audit_event)

    db.commit()
    db.refresh(approval)

    return _approval_to_response(approval)


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
def reject_approval(
    approval_id: UUID,
    request: ApprovalRejectRequest,
    reviewed_by: str = Query(..., description="User rejecting the action"),
    db: Session = Depends(get_db)
):
    """
    Reject an agent-proposed action.

    The proposed action is not executed. An audit event is logged.
    """
    approval = db.query(ApprovalQueue).filter(ApprovalQueue.id == approval_id).first()

    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Approval already {approval.status.value}"
        )

    # Mark as rejected
    rejection_notes = request.notes
    if request.reason:
        rejection_notes = f"{request.reason}: {request.notes}" if request.notes else request.reason

    approval.reject(reviewed_by=reviewed_by, notes=rejection_notes)

    # Create audit event
    audit_event = AuditEvent(
        event_type=AuditEventType.DECISION_RECORDED,  # Using existing type
        aggregate_type="approval",
        aggregate_id=approval.id,
        event_data={
            "action": "rejected",
            "action_type": approval.action_type.value,
            "proposed_by": approval.proposed_by,
            "reason": request.reason,
            "notes": request.notes
        },
        actor=reviewed_by
    )
    db.add(audit_event)

    db.commit()
    db.refresh(approval)

    return _approval_to_response(approval)


@router.get("/stats/summary")
def get_approval_stats(db: Session = Depends(get_db)):
    """Get summary statistics for the approval queue."""
    pending_count = db.query(ApprovalQueue).filter(
        ApprovalQueue.status == ApprovalStatus.PENDING
    ).count()

    approved_count = db.query(ApprovalQueue).filter(
        ApprovalQueue.status == ApprovalStatus.APPROVED
    ).count()

    rejected_count = db.query(ApprovalQueue).filter(
        ApprovalQueue.status == ApprovalStatus.REJECTED
    ).count()

    # Count by action type (pending only)
    pending_by_type = {}
    for action_type in ApprovalActionType:
        count = db.query(ApprovalQueue).filter(
            ApprovalQueue.status == ApprovalStatus.PENDING,
            ApprovalQueue.action_type == action_type
        ).count()
        if count > 0:
            pending_by_type[action_type.value] = count

    return {
        "pending": pending_count,
        "approved": approved_count,
        "rejected": rejected_count,
        "pending_by_type": pending_by_type
    }


# Helper functions

def _approval_to_response(approval: ApprovalQueue) -> ApprovalResponse:
    """Convert ApprovalQueue model to response schema."""
    return ApprovalResponse(
        id=approval.id,
        action_type=approval.action_type.value,
        payload=approval.payload,
        proposed_by=approval.proposed_by,
        proposed_at=approval.proposed_at,
        status=approval.status.value,
        reviewed_by=approval.reviewed_by,
        reviewed_at=approval.reviewed_at,
        review_notes=approval.review_notes,
        result_id=approval.result_id,
        trace_id=approval.trace_id,
        summary=approval.summary,
        confidence=approval.confidence
    )


def _execute_signal_approval(approval: ApprovalQueue, db: Session) -> UUID:
    """Create signal from approved proposal."""
    payload = approval.payload

    # Map reliability string to enum
    reliability_map = {
        "high": SignalReliability.HIGH,
        "medium": SignalReliability.MEDIUM,
        "low": SignalReliability.LOW,
        "unverified": SignalReliability.UNVERIFIED
    }
    reliability = reliability_map.get(payload.get("reliability", "medium").lower(), SignalReliability.MEDIUM)

    # Compute content hash
    from datetime import datetime
    observed_at = payload.get("observed_at")
    if isinstance(observed_at, str):
        observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))

    content_hash = compute_signal_content_hash(
        pack=payload["pack"],
        signal_type=payload["signal_type"],
        payload=payload["payload"],
        source=payload["source"],
        observed_at=observed_at
    )

    # Check for duplicate
    existing = db.query(Signal).filter(Signal.content_hash == content_hash).first()
    if existing:
        return existing.id

    # Create signal
    signal = Signal(
        pack=payload["pack"],
        signal_type=payload["signal_type"],
        payload=payload["payload"],
        source=payload["source"],
        reliability=reliability,
        observed_at=observed_at,
        signal_metadata={
            "extracted_by": approval.proposed_by,
            "source_spans": payload.get("source_spans", []),
            "extraction_notes": payload.get("extraction_notes"),
            "confidence": approval.confidence
        },
        content_hash=content_hash
    )

    db.add(signal)
    db.flush()

    # Create audit event for signal creation
    audit_event = AuditEvent(
        event_type=AuditEventType.SIGNAL_INGESTED,
        aggregate_type="signal",
        aggregate_id=signal.id,
        event_data={
            "signal_type": signal.signal_type,
            "source": signal.source,
            "pack": signal.pack,
            "extracted_by": approval.proposed_by,
            "approval_id": str(approval.id)
        },
        actor="system"
    )
    db.add(audit_event)

    return signal.id


def _execute_context_approval(approval: ApprovalQueue, db: Session):
    """Add context to exception from approved proposal."""
    from core.models import Exception as DBException

    payload = approval.payload
    exception_id = payload.get("exception_id")

    exception = db.query(DBException).filter(DBException.id == exception_id).first()
    if not exception:
        raise HTTPException(status_code=404, detail=f"Exception not found: {exception_id}")

    # Add context (merge with existing)
    context_key = payload.get("context_key")
    context_value = payload.get("context_value")

    if exception.context is None:
        exception.context = {}

    exception.context[context_key] = context_value
    db.flush()


def _execute_dismiss_approval(approval: ApprovalQueue, db: Session):
    """Dismiss exception from approved proposal."""
    from core.models import Exception as DBException, ExceptionStatus

    payload = approval.payload
    exception_id = payload.get("exception_id")

    exception = db.query(DBException).filter(DBException.id == exception_id).first()
    if not exception:
        raise HTTPException(status_code=404, detail=f"Exception not found: {exception_id}")

    from datetime import datetime
    exception.status = ExceptionStatus.DISMISSED
    exception.resolved_at = datetime.utcnow()

    # Store dismissal reason in context
    if exception.context is None:
        exception.context = {}
    exception.context["dismissal_reason"] = payload.get("reason")
    exception.context["dismissed_by_agent"] = approval.proposed_by

    db.flush()


def _execute_policy_draft_approval(approval: ApprovalQueue, db: Session) -> UUID:
    """Create policy version from approved draft."""
    from core.models import Policy, PolicyVersion, PolicyStatus
    from datetime import datetime

    payload = approval.payload

    # Check if updating existing policy or creating new one
    policy_id = payload.get("policy_id")

    if policy_id:
        # Updating existing policy
        policy = db.query(Policy).filter(Policy.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy not found: {policy_id}")
    else:
        # Create new policy
        policy = Policy(
            name=payload["name"],
            pack=payload.get("pack", "treasury"),
            description=payload["description"],
            created_by=f"agent:{approval.proposed_by}"
        )
        db.add(policy)
        db.flush()

    # Get current max version
    max_version = db.query(func.max(PolicyVersion.version_number)).filter(
        PolicyVersion.policy_id == policy.id
    ).scalar() or 0

    # Deactivate current version
    db.query(PolicyVersion).filter(
        PolicyVersion.policy_id == policy.id,
        PolicyVersion.status == PolicyStatus.ACTIVE
    ).update({"status": PolicyStatus.ARCHIVED})

    # Create new version
    version = PolicyVersion(
        policy_id=policy.id,
        version_number=max_version + 1,
        status=PolicyStatus.DRAFT,  # Starts as draft
        rule_definition=payload["rule_definition"],
        valid_from=datetime.utcnow(),
        changelog=payload.get("change_reason", "Agent-generated draft"),
        created_by=f"agent:{approval.proposed_by}"
    )
    db.add(version)
    db.flush()

    return version.id
