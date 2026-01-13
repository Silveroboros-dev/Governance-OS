"""
Policy and PolicyVersion models.

Policies are versioned rules with temporal validity.
Each policy can have multiple versions active at different times.
"""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, ForeignKey, CheckConstraint,
    UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.database import Base


class PolicyStatus(str, PyEnum):
    """Policy version status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"  # Changed from DEPRECATED to match database


class Policy(Base):
    """
    Policy: Named governance rule for a specific pack.

    A policy defines what to evaluate and when to raise exceptions.
    Policies are versioned - each policy can have multiple versions over time.
    """
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    pack = Column(String(50), nullable=False)  # 'treasury', 'wealth', etc.
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=False)

    # Relationships
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("name", "pack", name="uq_policy_name_pack"),
    )

    def __repr__(self):
        return f"<Policy(id={self.id}, name='{self.name}', pack='{self.pack}')>"


class PolicyVersion(Base):
    """
    PolicyVersion: Specific version of a policy with temporal validity.

    rule_definition contains the evaluation logic as JSON.
    Multiple versions can exist for a policy, each valid for different time ranges.
    """
    __tablename__ = "policy_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    status = Column(SQLEnum(PolicyStatus, name="policy_status", values_callable=lambda x: [e.value for e in x]), nullable=False, default=PolicyStatus.DRAFT)

    # Policy logic stored as JSON (deterministic evaluation rules)
    rule_definition = Column(JSONB, nullable=False)

    # Temporal validity
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_to = Column(DateTime(timezone=True), nullable=True)  # NULL means currently active

    # Metadata
    changelog = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)

    # Relationships
    policy = relationship("Policy", back_populates="versions")
    evaluations = relationship("Evaluation", back_populates="policy_version")

    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_version_number"),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_policy_version_valid_dates"
        ),
    )

    def __repr__(self):
        return f"<PolicyVersion(id={self.id}, policy_id={self.policy_id}, version={self.version_number}, status='{self.status}')>"
