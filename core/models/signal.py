"""
Signal model.

Signals are timestamped facts with provenance.
They represent observations from external systems or internal processes.
"""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, CheckConstraint, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.database import Base


class SignalReliability(str, PyEnum):
    """Signal reliability classification."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class Signal(Base):
    """
    Signal: Timestamped fact with provenance.

    Signals are the inputs to the governance kernel.
    Each signal has structured payload data, source tracking, and reliability classification.
    """
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    pack = Column(String(50), nullable=False)
    signal_type = Column(String(100), nullable=False)  # e.g., 'position_limit_breach', 'market_volatility_spike'

    # Signal payload (structured data)
    payload = Column(JSONB, nullable=False)

    # Provenance
    source = Column(String(255), nullable=False)  # e.g., 'bloomberg_api', 'internal_system'
    reliability = Column(SQLEnum(SignalReliability, name="signal_reliability"), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)  # When signal was observed
    ingested_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)  # When we received it

    # Metadata (renamed to avoid SQLAlchemy reserved attribute)
    signal_metadata = Column("metadata", JSONB)  # Additional context (e.g., data provider, user who submitted)

    __table_args__ = (
        CheckConstraint("observed_at <= ingested_at", name="ck_signal_observed_before_ingested"),
        Index("idx_signals_type_time", "pack", "signal_type", "observed_at"),
        Index("idx_signals_ingested", "ingested_at"),
    )

    def __repr__(self):
        return f"<Signal(id={self.id}, type='{self.signal_type}', pack='{self.pack}', observed_at={self.observed_at})>"
