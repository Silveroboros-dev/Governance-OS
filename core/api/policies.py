"""
Policies API Router.

Handles listing, retrieving, and versioning governance policies.
Supports the draft → replay → compare → publish workflow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from core.database import get_db
from core.models import Policy, PolicyVersion, PolicyStatus, AuditEvent, AuditEventType
from core.schemas.policy import (
    PolicyWithVersion,
    PolicyVersionCreate,
    PolicyVersionResponse,
    DraftVersionCreate,
    DraftVersionResponse,
    PolicyVersionPublish,
)
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


# =============================================================================
# Draft Workflow Endpoints
# =============================================================================

@router.get("/{policy_id}/versions", response_model=List[PolicyVersionResponse])
def list_policy_versions(
    policy_id: str,
    status: Optional[str] = Query(default=None, description="Filter by status: draft, active, archived"),
    db: Session = Depends(get_db)
):
    """
    List all versions of a policy.

    Useful for viewing version history and finding drafts.
    """
    try:
        policy_uuid = UUID(policy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    policy = db.query(Policy).filter(Policy.id == policy_uuid).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    query = db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy_uuid)

    if status:
        status_map = {
            "draft": PolicyStatus.DRAFT,
            "active": PolicyStatus.ACTIVE,
            "archived": PolicyStatus.ARCHIVED
        }
        status_enum = status_map.get(status.lower())
        if status_enum:
            query = query.filter(PolicyVersion.status == status_enum)

    versions = query.order_by(PolicyVersion.version_number.desc()).all()
    return versions


@router.post("/{policy_id}/versions/draft", response_model=DraftVersionResponse, status_code=201)
def create_draft_version(
    policy_id: str,
    draft_data: DraftVersionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a draft version of a policy for testing.

    Draft versions can be replayed against historical signals
    without affecting production evaluations.

    Workflow:
    1. Create draft with modified rule_definition
    2. Run replay with draft version
    3. Compare results with active version
    4. Publish draft or discard
    """
    try:
        policy_uuid = UUID(policy_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    policy = db.query(Policy).options(joinedload(Policy.versions)).filter(Policy.id == policy_uuid).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Find current max version number
    max_version = max((v.version_number for v in policy.versions), default=0)

    # Check for existing draft
    existing_draft = next(
        (v for v in policy.versions if v.status == PolicyStatus.DRAFT),
        None
    )
    if existing_draft:
        raise HTTPException(
            status_code=400,
            detail=f"Policy already has a draft version (v{existing_draft.version_number}). "
                   "Publish or delete it before creating a new draft."
        )

    # Create draft version
    draft_version = PolicyVersion(
        policy_id=policy_uuid,
        version_number=max_version + 1,
        status=PolicyStatus.DRAFT,
        rule_definition=draft_data.rule_definition,
        valid_from=datetime.now(timezone.utc),
        valid_to=None,
        changelog=draft_data.changelog,
        created_by=draft_data.created_by
    )
    db.add(draft_version)

    # Audit event
    audit_event = AuditEvent(
        event_type=AuditEventType.POLICY_CREATED,
        aggregate_type="policy_version",
        aggregate_id=draft_version.id,
        event_data={
            "policy_id": str(policy_uuid),
            "policy_name": policy.name,
            "version_number": draft_version.version_number,
            "status": "draft",
            "changelog": draft_data.changelog
        },
        actor=draft_data.created_by
    )
    db.add(audit_event)
    db.commit()
    db.refresh(draft_version)

    # Compute diff summary from active version
    diff_summary = None
    now = datetime.now(timezone.utc)
    active_version = next(
        (v for v in policy.versions
         if v.status == PolicyStatus.ACTIVE
         and v.valid_from <= now
         and (v.valid_to is None or v.valid_to > now)),
        None
    )
    if active_version:
        diff_summary = _compute_rule_diff(
            active_version.rule_definition,
            draft_data.rule_definition
        )

    return DraftVersionResponse(
        id=draft_version.id,
        policy_id=policy_uuid,
        policy_name=policy.name,
        version_number=draft_version.version_number,
        status=draft_version.status.value,
        rule_definition=draft_version.rule_definition,
        changelog=draft_version.changelog,
        created_at=draft_version.created_at,
        created_by=draft_version.created_by,
        diff_summary=diff_summary
    )


@router.get("/{policy_id}/versions/{version_id}", response_model=PolicyVersionResponse)
def get_policy_version(
    policy_id: str,
    version_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific policy version by ID.
    """
    try:
        policy_uuid = UUID(policy_id)
        version_uuid = UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    version = db.query(PolicyVersion).filter(
        PolicyVersion.id == version_uuid,
        PolicyVersion.policy_id == policy_uuid
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Policy version not found")

    return version


@router.post("/{policy_id}/versions/{version_id}/publish", response_model=PolicyVersionResponse)
def publish_draft_version(
    policy_id: str,
    version_id: str,
    publish_data: PolicyVersionPublish,
    db: Session = Depends(get_db)
):
    """
    Publish a draft version, making it active.

    This will:
    1. Archive the current active version (set valid_to)
    2. Set the draft to active status
    3. Set valid_from to now (or specified time)
    """
    try:
        policy_uuid = UUID(policy_id)
        version_uuid = UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    policy = db.query(Policy).options(joinedload(Policy.versions)).filter(Policy.id == policy_uuid).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    draft = db.query(PolicyVersion).filter(
        PolicyVersion.id == version_uuid,
        PolicyVersion.policy_id == policy_uuid
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Policy version not found")

    if draft.status != PolicyStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft versions can be published")

    now = publish_data.valid_from or datetime.now(timezone.utc)

    # Archive current active version
    for version in policy.versions:
        if version.status == PolicyStatus.ACTIVE and version.valid_to is None:
            version.valid_to = now
            version.status = PolicyStatus.ARCHIVED

    # Activate draft
    draft.status = PolicyStatus.ACTIVE
    draft.valid_from = now
    if publish_data.changelog:
        draft.changelog = f"{draft.changelog or ''}\n\nPublished: {publish_data.changelog}".strip()

    # Audit event
    audit_event = AuditEvent(
        event_type=AuditEventType.POLICY_ACTIVATED,
        aggregate_type="policy_version",
        aggregate_id=draft.id,
        event_data={
            "policy_id": str(policy_uuid),
            "policy_name": policy.name,
            "version_number": draft.version_number,
            "valid_from": now.isoformat()
        },
        actor="system"  # TODO: Get from auth context
    )
    db.add(audit_event)
    db.commit()
    db.refresh(draft)

    return draft


@router.delete("/{policy_id}/versions/{version_id}", status_code=204)
def delete_draft_version(
    policy_id: str,
    version_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a draft version.

    Only draft versions can be deleted. Active/archived versions are immutable.
    """
    try:
        policy_uuid = UUID(policy_id)
        version_uuid = UUID(version_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    version = db.query(PolicyVersion).filter(
        PolicyVersion.id == version_uuid,
        PolicyVersion.policy_id == policy_uuid
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Policy version not found")

    if version.status != PolicyStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft versions can be deleted")

    db.delete(version)
    db.commit()


def _compute_rule_diff(baseline: Dict[str, Any], comparison: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a summary of differences between two rule definitions."""
    diff = {
        "added": [],
        "removed": [],
        "changed": [],
        "unchanged": []
    }

    baseline_keys = set(baseline.keys())
    comparison_keys = set(comparison.keys())

    # Added keys
    for key in comparison_keys - baseline_keys:
        diff["added"].append(key)

    # Removed keys
    for key in baseline_keys - comparison_keys:
        diff["removed"].append(key)

    # Changed/unchanged keys
    for key in baseline_keys & comparison_keys:
        if baseline[key] != comparison[key]:
            diff["changed"].append(key)
        else:
            diff["unchanged"].append(key)

    diff["has_changes"] = bool(diff["added"] or diff["removed"] or diff["changed"])
    return diff
