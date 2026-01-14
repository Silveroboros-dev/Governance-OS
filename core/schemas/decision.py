"""
Pydantic schemas for Decision API.
"""

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DecisionCreate(BaseModel):
    """Schema for creating a decision."""
    exception_id: UUID = Field(..., description="Exception being resolved")
    chosen_option_id: str = Field(..., description="ID of chosen option")
    rationale: str = Field(..., min_length=10, description="Decision rationale (required, min 10 chars)")
    assumptions: Optional[str] = Field(None, description="Explicit assumptions (optional)")
    decided_by: str = Field(..., description="User/role who made the decision")

    # Hard override fields
    is_hard_override: bool = Field(False, description="True if this overrides policy recommendation")

    # Approval (required if is_hard_override=True)
    approved_by: Optional[str] = Field(None, description="Approver username (required for hard overrides)")
    approval_notes: Optional[str] = Field(None, description="Approver's justification")

    @model_validator(mode='after')
    def validate_hard_override_approval(self):
        """Ensure hard overrides have approval."""
        if self.is_hard_override and not self.approved_by:
            raise ValueError("Hard overrides require approved_by")
        return self


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

    # Hard override fields
    decision_type: str = "standard"
    is_hard_override: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_notes: Optional[str] = None

    class Config:
        from_attributes = True


class DecisionListItem(BaseModel):
    """Schema for decision in list view."""
    id: UUID
    exception_id: UUID
    chosen_option_id: str
    decided_by: str
    decided_at: datetime
    is_hard_override: bool = False

    class Config:
        from_attributes = True


class ApprovalCheck(BaseModel):
    """Response for checking if user can approve."""
    user: str
    can_approve: bool
    reason: Optional[str] = None
