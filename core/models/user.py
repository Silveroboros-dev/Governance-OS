"""
User and Role models (minimal stub for authorization).

This is a stub for Sprint 2 hard override approval.
Full auth implementation planned for Sprint 3.
"""

from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class UserRole(str, PyEnum):
    """User roles for governance authorization."""
    VIEWER = "viewer"      # Can view exceptions and decisions
    DECIDER = "decider"    # Can make standard decisions
    APPROVER = "approver"  # Can approve hard overrides
    ADMIN = "admin"        # Full access


class User(Base):
    """
    User: Identity for accountability and authorization.

    Minimal stub for Sprint 2. Full implementation in Sprint 3.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)

    # Role-based authorization
    role = Column(
        SQLEnum(UserRole, name="user_role", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.VIEWER
    )

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

    def can_decide(self) -> bool:
        """Check if user can make standard decisions."""
        return self.role in (UserRole.DECIDER, UserRole.APPROVER, UserRole.ADMIN)

    def can_approve(self) -> bool:
        """Check if user can approve hard overrides."""
        return self.role in (UserRole.APPROVER, UserRole.ADMIN)

    def can_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role == UserRole.ADMIN
