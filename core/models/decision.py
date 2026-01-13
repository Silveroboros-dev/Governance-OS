"""
Decision model.

Decisions are immutable commitments with rationale.
Once recorded, they CANNOT be modified.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class Decision(Base):
    """
    Decision: Immutable commitment with rationale.

    CRITICAL: Decisions are IMMUTABLE.
    - No UPDATE operations allowed after creation
    - Enforced at ORM level and database permission level
    - Accountability via decided_by and decided_at
    """
    __tablename__ = "decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    exception_id = Column(UUID(as_uuid=True), ForeignKey("exceptions.id"), nullable=False)

    # Immutable decision record
    chosen_option_id = Column(String(100), nullable=False)  # References options[].id from exception
    rationale = Column(Text, nullable=False)  # Human explanation (required!)
    assumptions = Column(Text, nullable=True)  # Explicit assumptions made (optional)

    # Accountability
    decided_by = Column(String(255), nullable=False)  # User/role who made decision
    decided_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Evidence link (can be generated async, so nullable initially)
    evidence_pack_id = Column(UUID(as_uuid=True), ForeignKey("evidence_packs.id"), nullable=True)

    # Relationships
    exception = relationship("Exception", back_populates="decisions")
    evidence_pack = relationship("EvidencePack", back_populates="decision", uselist=False)

    __table_args__ = (
        Index("idx_decisions_exception", "exception_id"),
        Index("idx_decisions_timestamp", "decided_at"),
    )

    def __repr__(self):
        return f"<Decision(id={self.id}, exception_id={self.exception_id}, decided_by='{self.decided_by}', decided_at={self.decided_at})>"
