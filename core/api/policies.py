"""
Policies API Router.

Handles listing and retrieving governance policies (read-only).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from core.database import get_db
from core.models import Policy, PolicyVersion, PolicyStatus
from core.schemas.policy import PolicyWithVersion
from core.api.dependencies import get_required_pack

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=List[PolicyWithVersion])
def list_policies(
    pack: str = Depends(get_required_pack),
    status: Optional[str] = Query(default=None, description="Filter by status: draft, active, archived"),
    limit: int = Query(default=100, le=200),
    db: Session = Depends(get_db)
):
    """
    List policies with their active versions.

    Pack is required to enforce pack isolation.
    Returns policies with their currently active policy version based on temporal validity.
    """
    query = db.query(Policy).options(joinedload(Policy.versions))

    # Filter by pack (required)
    query = query.filter(Policy.pack == pack)

    policies = query.limit(limit).all()

    # Build response with active version
    result = []
    now = datetime.now(timezone.utc)

    for policy in policies:
        # Find the active version (status=active and valid at current time)
        active_version = None
        for version in policy.versions:
            if version.status == PolicyStatus.ACTIVE:
                if version.valid_from <= now and (version.valid_to is None or version.valid_to > now):
                    active_version = version
                    break

        # If status filter is specified, only include if active_version matches
        if status:
            status_map = {
                "draft": PolicyStatus.DRAFT,
                "active": PolicyStatus.ACTIVE,
                "archived": PolicyStatus.ARCHIVED
            }
            status_enum = status_map.get(status.lower())
            if status_enum:
                if active_version is None or active_version.status != status_enum:
                    continue

        policy_dict = {
            "id": policy.id,
            "name": policy.name,
            "pack": policy.pack,
            "description": policy.description,
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
            "created_by": policy.created_by,
            "active_version": active_version
        }
        result.append(policy_dict)

    return result


@router.get("/{policy_id}", response_model=PolicyWithVersion)
def get_policy(
    policy_id: str,
    db: Session = Depends(get_db)
):
    """
    Get policy with its active version.
    """
    try:
        policy_uuid = UUID(policy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    policy = db.query(Policy).options(joinedload(Policy.versions)).filter(Policy.id == policy_uuid).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Find active version
    now = datetime.now(timezone.utc)
    active_version = None
    for version in policy.versions:
        if version.status == PolicyStatus.ACTIVE:
            if version.valid_from <= now and (version.valid_to is None or version.valid_to > now):
                active_version = version
                break

    policy_dict = {
        "id": policy.id,
        "name": policy.name,
        "pack": policy.pack,
        "description": policy.description,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
        "created_by": policy.created_by,
        "active_version": active_version
    }

    return policy_dict
