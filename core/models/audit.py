"""
AuditEvent model.

Audit events provide an append-only trail of meaningful state changes.
"""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.database import Base


class AuditEventType(str, PyEnum):
    """Types of audit events."""
    SIGNAL_INGESTED = "signal_ingested"
    POLICY_CREATED = "policy_created"
    POLICY_VERSION_PUBLISHED = "policy_version_published"
    EVALUATION_EXECUTED = "evaluation_executed"
    EXCEPTION_RAISED = "exception_raised"
    DECISION_RECORDED = "decision_recorded"
    EVIDENCE_PACK_GENERATED = "evidence_pack_generated"


class AuditEvent(Base):
    """
    AuditEvent: Append-only trail of state changes.

    Audit events are NEVER modified or deleted.
    They provide complete traceability for compliance and debugging.
    """
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(SQLEnum(AuditEventType, name="audit_event_type"), nullable=False)

    # References to domain objects
    aggregate_type = Column(String(50), nullable=False)  # 'signal', 'policy', 'exception', 'decision'
    aggregate_id = Column(UUID(as_uuid=True), nullable=False)

    # Event payload (structured data about what changed)
    event_data = Column(JSONB, nullable=False)

    # Provenance
    actor = Column(String(255), nullable=True)  # User/system that caused event
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Replay support
    replay_namespace = Column(String(100), default="production")

    __table_args__ = (
        Index("idx_audit_events_aggregate", "aggregate_type", "aggregate_id", "occurred_at"),
        Index("idx_audit_events_type", "event_type", "occurred_at"),
    )

    def __repr__(self):
        return f"<AuditEvent(id={self.id}, type='{self.event_type}', aggregate='{self.aggregate_type}:{self.aggregate_id}')>"
