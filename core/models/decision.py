"""
Decision model.

Decisions are immutable commitments with rationale.
Once recorded, they CANNOT be modified.
"""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, Boolean, Enum as SQLEnum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class DecisionType(str, PyEnum):
    """Type of decision based on governance rules."""
    STANDARD = "standard"       # Normal decision flow
    HARD_OVERRIDE = "hard_override"  # Overrides policy recommendation, requires approval


class Decision(Base):
    """
    Decision: Immutable commitment with rationale.

    CRITICAL: Decisions are IMMUTABLE.
    - No UPDATE operations allowed after creation
    - Enforced at ORM level and database permission level
    - Accountability via decided_by and decided_at
    - Hard overrides require separate approval
    """
    __tablename__ = "decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(UUID(as_uuid=True), ForeignKey("exceptions.id"), nullable=False)

    # Immutable decision record
    chosen_option_id = Column(String(100), nullable=False)  # References options[].id from exception
    rationale = Column(Text, nullable=False)  # Human explanation (required!)
    assumptions = Column(Text, nullable=True)  # Explicit assumptions made (optional)

    # Decision type and override tracking
    decision_type = Column(
        SQLEnum(DecisionType, name="decision_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DecisionType.STANDARD
    )
    is_hard_override = Column(Boolean, nullable=False, default=False)  # Convenience flag

    # Accountability - Decider
    decided_by = Column(String(255), nullable=False)  # User/role who made decision
    decided_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Accountability - Approver (required for hard overrides)
    approved_by = Column(String(255), nullable=True)  # User with Approver role
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)  # Approver's justification

    # Evidence link (can be generated async, so nullable initially)
    evidence_pack_id = Column(UUID(as_uuid=True), ForeignKey("evidence_packs.id"), nullable=True)

    # Relationships
    exception = relationship("Exception", back_populates="decisions")
    # Note: evidence_pack relationship is accessed via EvidencePack.decision relationship
    # to avoid circular dependency issues with bidirectional foreign keys

    __table_args__ = (
        Index("idx_decisions_exception", "exception_id"),
        Index("idx_decisions_timestamp", "decided_at"),
        # Hard overrides MUST have approval
        CheckConstraint(
            "(is_hard_override = false) OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_hard_override_requires_approval"
        ),
    )

    def __repr__(self):
        return f"<Decision(id={self.id}, exception_id={self.exception_id}, decided_by='{self.decided_by}', decided_at={self.decided_at})>"
