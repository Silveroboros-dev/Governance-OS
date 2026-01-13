"""
Evaluation model.

Evaluations are deterministic results of applying policies to signals.
"""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from core.database import Base


class EvaluationResult(str, PyEnum):
    """Evaluation result classification."""
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class Evaluation(Base):
    """
    Evaluation: Deterministic result of applying policy to signals.

    CRITICAL: Evaluations must be deterministic.
    - input_hash ensures idempotency: same inputs → same hash → same evaluation
    - signal_ids array preserves order for determinism
    """
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    policy_version_id = Column(UUID(as_uuid=True), ForeignKey("policy_versions.id"), nullable=False)

    # Signals that were evaluated (array of UUIDs, preserves order for determinism)
    signal_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)

    # Result
    result = Column(SQLEnum(EvaluationResult, name="evaluation_result"), nullable=False)
    details = Column(JSONB, nullable=False)  # Structured explanation of evaluation

    # Determinism guarantee: hash of inputs
    # SHA256 of (policy_version_id + sorted signal_ids + signal payloads)
    input_hash = Column(String(64), nullable=False)

    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # For replay: namespace allows running parallel evaluations
    replay_namespace = Column(String(100), default="production")

    # Relationships
    policy_version = relationship("PolicyVersion", back_populates="evaluations")
    exceptions = relationship("Exception", back_populates="evaluation")

    __table_args__ = (
        Index("idx_evaluations_policy", "policy_version_id", "evaluated_at"),
        Index("idx_evaluations_hash", "input_hash"),  # Dedupe check
    )

    def __repr__(self):
        return f"<Evaluation(id={self.id}, result='{self.result}', hash='{self.input_hash[:8]}...')>"
