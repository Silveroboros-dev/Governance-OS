"""
Pydantic schemas for Policy API.
"""

from datetime import datetime
from typing import Optional, Dict, Any
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
