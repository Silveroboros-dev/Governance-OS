"""
Policy Engine Service.

Responsible for loading active policy versions at given timestamps.
Provides temporal policy resolution with deterministic results.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models import PolicyVersion, PolicyStatus


class PolicyEngine:
    """
    Policy engine for loading and managing policy versions.

    Provides temporal policy resolution: given a timestamp,
    returns the policy versions that were active at that time.
    """

    def __init__(self, db: Session):
        """
        Initialize policy engine.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_active_policies(
        self,
        pack: str,
        as_of: Optional[datetime] = None
    ) -> List[PolicyVersion]:
        """
        Get all active policy versions for a pack at a given timestamp.

        This is deterministic: same timestamp always returns same policies.

        Args:
            pack: Pack name (e.g., 'treasury', 'wealth')
            as_of: Timestamp to query (defaults to now)

        Returns:
            List of active PolicyVersion objects

        Example:
            >>> engine = PolicyEngine(db)
            >>> policies = engine.get_active_policies("treasury")
            >>> len(policies)
            2
        """
        if as_of is None:
            as_of = datetime.utcnow()

        # Query for active policy versions valid at the given timestamp
        query = (
            self.db.query(PolicyVersion)
            .join(PolicyVersion.policy)
            .filter(
                PolicyVersion.status == PolicyStatus.ACTIVE,
                PolicyVersion.valid_from <= as_of,
                # valid_to is NULL (still active) or greater than as_of
                (PolicyVersion.valid_to.is_(None) | (PolicyVersion.valid_to > as_of))
            )
            .filter(PolicyVersion.policy.has(pack=pack))
            .order_by(PolicyVersion.policy_id, PolicyVersion.version_number.desc())
        )

        return query.all()

    def get_policy_version(
        self,
        policy_id: UUID,
        as_of: Optional[datetime] = None
    ) -> Optional[PolicyVersion]:
        """
        Get specific policy version valid at timestamp.

        Args:
            policy_id: UUID of the policy
            as_of: Timestamp to query (defaults to now)

        Returns:
            PolicyVersion object or None if not found

        Example:
            >>> version = engine.get_policy_version(policy_id)
            >>> version.version_number
            3
        """
        if as_of is None:
            as_of = datetime.utcnow()

        return (
            self.db.query(PolicyVersion)
            .filter(
                PolicyVersion.policy_id == policy_id,
                PolicyVersion.status == PolicyStatus.ACTIVE,
                PolicyVersion.valid_from <= as_of,
                (PolicyVersion.valid_to.is_(None) | (PolicyVersion.valid_to > as_of))
            )
            .order_by(PolicyVersion.version_number.desc())
            .first()
        )

    def get_policy_version_by_id(
        self,
        version_id: UUID
    ) -> Optional[PolicyVersion]:
        """
        Get policy version by its UUID.

        Args:
            version_id: UUID of the policy version

        Returns:
            PolicyVersion object or None if not found
        """
        return (
            self.db.query(PolicyVersion)
            .filter(PolicyVersion.id == version_id)
            .first()
        )
