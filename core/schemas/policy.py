"""
Pydantic schemas for Policy API.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""
    name: str = Field(..., max_length=255)
    pack: str = Field(..., max_length=50)
    description: Optional[str] = None
    created_by: str


class PolicyResponse(BaseModel):
    """Schema for policy response."""
    id: UUID
    name: str
    pack: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class PolicyVersionCreate(BaseModel):
    """Schema for creating a policy version."""
    policy_id: UUID
    version_number: int
    rule_definition: Dict[str, Any]
    valid_from: datetime
    valid_to: Optional[datetime] = None
    changelog: Optional[str] = None
    created_by: str


class PolicyVersionResponse(BaseModel):
    """Schema for policy version response."""
    id: UUID
    policy_id: UUID
    version_number: int
    status: str
    rule_definition: Dict[str, Any]
    valid_from: datetime
    valid_to: Optional[datetime] = None
    changelog: Optional[str] = None
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True


class PolicyWithVersion(PolicyResponse):
    """Schema for policy with its active version."""
    active_version: Optional[PolicyVersionResponse] = None

    class Config:
        from_attributes = True


# Draft workflow schemas

class DraftVersionCreate(BaseModel):
    """Schema for creating a draft policy version from existing version."""
    rule_definition: Dict[str, Any] = Field(..., description="New rule definition to test")
    changelog: Optional[str] = Field(None, description="Description of changes")
    created_by: str = Field(..., description="User creating the draft")


class DraftVersionResponse(BaseModel):
    """Schema for draft version response."""
    id: UUID
    policy_id: UUID
    policy_name: str
    version_number: int
    status: str
    rule_definition: Dict[str, Any]
    changelog: Optional[str] = None
    created_at: datetime
    created_by: str
    # Diff from active version
    diff_summary: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class PolicyVersionPublish(BaseModel):
    """Schema for publishing a draft version."""
    valid_from: Optional[datetime] = Field(None, description="When the version becomes active. Default: now")
    changelog: Optional[str] = Field(None, description="Additional changelog notes")


class PolicyVersionCompare(BaseModel):
    """Schema for comparing two policy versions."""
    baseline_version_id: UUID
    comparison_version_id: UUID


class PolicyVersionDiff(BaseModel):
    """Schema for policy version diff result."""
    baseline_version_id: UUID
    comparison_version_id: UUID
    baseline_version_number: int
    comparison_version_number: int
    rule_changes: Dict[str, Any] = Field(default_factory=dict)
    has_changes: bool = True


# Replay with draft schemas

class ReplayRequest(BaseModel):
    """Schema for triggering a replay evaluation."""
    pack: str = Field(..., description="Pack to replay (treasury, wealth)")
    policy_version_id: Optional[UUID] = Field(None, description="Specific version to test (draft allowed)")
    signal_ids: Optional[List[UUID]] = Field(None, description="Specific signals to replay. Default: last 24h")
    from_date: Optional[datetime] = Field(None, description="Start date for signal selection")
    to_date: Optional[datetime] = Field(None, description="End date for signal selection")


class ReplayResultSummary(BaseModel):
    """Summary of replay results."""
    replay_id: str
    policy_version_id: UUID
    policy_name: str
    version_number: int
    is_draft: bool
    signals_processed: int
    pass_count: int
    fail_count: int
    inconclusive_count: int
    exceptions_raised: int
    executed_at: datetime


class ComparisonRequest(BaseModel):
    """Schema for comparing two replay results."""
    baseline_replay_id: str = Field(..., description="ID of baseline replay (typically active version)")
    comparison_replay_id: str = Field(..., description="ID of comparison replay (typically draft version)")


class ComparisonResultSummary(BaseModel):
    """Summary of comparison between two replay runs."""
    baseline_replay_id: str
    comparison_replay_id: str
    baseline_version_number: int
    comparison_version_number: int
    # Exception counts
    baseline_exceptions: int
    comparison_exceptions: int
    new_exceptions: int
    resolved_exceptions: int
    # Net change
    exception_delta: int
    # Evaluation comparison
    total_evaluations: int
    matching_evaluations: int
    divergent_evaluations: int
    # Summary
    summary: str
