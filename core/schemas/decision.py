"""
Pydantic schemas for Decision API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DecisionCreate(BaseModel):
    """Schema for creating a decision."""
    exception_id: UUID = Field(..., description="Exception being resolved")
    chosen_option_id: str = Field(..., description="ID of chosen option")
    rationale: str = Field(..., min_length=10, description="Decision rationale (required, min 10 chars)")
    assumptions: Optional[str] = Field(None, description="Explicit assumptions (optional)")
    decided_by: str = Field(..., description="User/role who made the decision")


class DecisionResponse(BaseModel):
    """Schema for decision response."""
    id: UUID
    exception_id: UUID
    chosen_option_id: str
    rationale: str
    assumptions: Optional[str] = None
    decided_by: str
    decided_at: datetime
    evidence_pack_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class DecisionListItem(BaseModel):
    """Schema for decision in list view."""
    id: UUID
    exception_id: UUID
    chosen_option_id: str
    decided_by: str
    decided_at: datetime

    class Config:
        from_attributes = True
