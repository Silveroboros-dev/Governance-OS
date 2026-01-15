"""
ApprovalQueue model.

Sprint 3: Gated write operations for agent-proposed actions.
All agent writes go through approval queue for human review.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Float, Text, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.database import Base


class ApprovalActionType(str, PyEnum):
    """Types of actions that can be proposed by agents."""
    SIGNAL = "signal"              # propose_signal: Create candidate signal
    POLICY_DRAFT = "policy_draft"  # propose_policy_draft: Create draft policy version
    DECISION = "decision"          # propose_decision: Suggest decision (no recommendation)
    DISMISS = "dismiss"            # dismiss_exception: Mark exception as dismissed
    CONTEXT = "context"            # add_exception_context: Enrich exception


class ApprovalStatus(str, PyEnum):
    """Status of approval requests."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalQueue(Base):
    """
    ApprovalQueue: Gated write operations requiring human review.

    All agent-proposed writes create entries here. No direct database
    mutations from agents are allowed.

    Safety invariants:
    - All writes create pending_approval records
    - Every approval/rejection logged to AuditEvent
    - Approval UI shows full agent reasoning
    """
    __tablename__ = "approval_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # What action is being proposed
    action_type = Column(
        SQLEnum(ApprovalActionType, name="approval_action_type",
                values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # The proposed data (schema depends on action_type)
    payload = Column(JSONB, nullable=False)

    # Agent that proposed this action
    proposed_by = Column(String(100), nullable=False)
    proposed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Approval status
    status = Column(
        SQLEnum(ApprovalStatus, name="approval_status",
                values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ApprovalStatus.PENDING
    )

    # Review information (filled when approved/rejected)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Result of approval (ID of created entity)
    result_id = Column(UUID(as_uuid=True), nullable=True)

    # Link to agent trace for observability
    trace_id = Column(UUID(as_uuid=True), ForeignKey("agent_traces.id", ondelete="SET NULL"), nullable=True)

    # Display helpers
    summary = Column(String(500), nullable=True)  # Human-readable summary
    confidence = Column(Float, nullable=True)  # 0.0-1.0 for signal extractions

    # Relationships
    trace = relationship("AgentTrace", back_populates="approvals")

    __table_args__ = (
        Index("idx_approval_queue_status", "status"),
        Index("idx_approval_queue_action_type", "action_type"),
        Index("idx_approval_queue_proposed_at", "proposed_at"),
        Index("idx_approval_queue_trace", "trace_id"),
    )

    def __repr__(self):
        return f"<ApprovalQueue(id={self.id}, type='{self.action_type.value}', status='{self.status.value}')>"

    def approve(self, reviewed_by: str, result_id: Optional[UUID] = None, notes: Optional[str] = None):
        """Mark this approval as approved."""
        self.status = ApprovalStatus.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        self.result_id = result_id
        if notes:
            self.review_notes = notes

    def reject(self, reviewed_by: str, notes: Optional[str] = None):
        """Mark this approval as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = datetime.utcnow()
        if notes:
            self.review_notes = notes
