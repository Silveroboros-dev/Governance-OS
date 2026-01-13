"""
EvidencePack model.

Evidence packs are deterministic audit bundles for decisions.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.database import Base


class EvidencePack(Base):
    """
    EvidencePack: Deterministic audit bundle for a decision.

    Evidence packs are self-contained JSON documents that include:
    - The decision and its rationale
    - The exception that triggered the decision
    - The evaluation that raised the exception
    - All signals that contributed to the evaluation
    - The policy version that was applied
    - Complete audit trail

    content_hash ensures integrity and determinism.
    """
    __tablename__ = "evidence_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False)

    # Complete evidence bundle (JSON structure with all referenced data)
    evidence = Column(JSONB, nullable=False)

    # Determinism guarantee: SHA256 of evidence JSON (canonical ordering)
    content_hash = Column(String(64), nullable=False)

    generated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    decision = relationship("Decision", foreign_keys="[EvidencePack.decision_id]")

    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_evidence_pack_decision"),
        Index("idx_evidence_packs_decision", "decision_id"),
    )

    def __repr__(self):
        return f"<EvidencePack(id={self.id}, decision_id={self.decision_id}, hash='{self.content_hash[:8]}...')>"
