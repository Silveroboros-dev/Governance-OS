"""
Exception model.

Exceptions are interruptions requiring human judgment.
They are deduplicated using fingerprints.
"""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.database import Base


class ExceptionSeverity(str, PyEnum):
    """Exception severity classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExceptionStatus(str, PyEnum):
    """Exception lifecycle status."""
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Exception(Base):
    """
    Exception: Interruption requiring human judgment.

    Exceptions are deduplicated using fingerprints:
    - fingerprint is a deterministic hash of (policy + exception type + key dimensions)
    - Same fingerprint while open = duplicate (blocked)
    - Same fingerprint after resolution = can recur

    Options are ALWAYS symmetric (no ranking, no "recommended" flag).
    """
    __tablename__ = "exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False)

    # Deduplication fingerprint (deterministic hash of exception "sameness")
    # SHA256 of (policy + exception type + key dimensions)
    fingerprint = Column(String(64), nullable=False)

    severity = Column(SQLEnum(ExceptionSeverity, name="exception_severity", values_callable=lambda x: [e.value for e in x]), nullable=False)
    status = Column(SQLEnum(ExceptionStatus, name="exception_status", values_callable=lambda x: [e.value for e in x]), nullable=False, default=ExceptionStatus.OPEN)

    # Human-readable context
    title = Column(String(500), nullable=False)
    context = Column(JSONB, nullable=False)  # Structured data for UI presentation

    # Options presented to decision maker (symmetric, no ranking)
    # Structure: [{"id": "...", "label": "...", "description": "...", "implications": ["...", ...]}, ...]
    options = Column(JSONB, nullable=False)

    raised_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    evaluation = relationship("Evaluation", back_populates="exceptions")
    decisions = relationship("Decision", back_populates="exception")

    __table_args__ = (
        UniqueConstraint("fingerprint", "resolved_at", name="uq_exception_fingerprint_resolved"),
        Index("idx_exceptions_status", "status", "severity", "raised_at"),
        Index("idx_exceptions_fingerprint", "fingerprint", "resolved_at"),
    )

    def __repr__(self):
        return f"<Exception(id={self.id}, severity='{self.severity}', status='{self.status}', title='{self.title[:30]}...')>"
