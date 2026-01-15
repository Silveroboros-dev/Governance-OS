"""
Pydantic schemas for Approval Queue API.

Sprint 3: Schemas for agent-proposed actions requiring human review.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalBase(BaseModel):
    """Base schema for approval queue items."""
    action_type: str = Field(..., description="Type: signal, policy_draft, decision, dismiss, context")
    payload: Dict[str, Any] = Field(..., description="Proposed data (schema depends on action_type)")
    proposed_by: str = Field(..., description="Agent identifier that proposed this action")
    summary: Optional[str] = Field(None, description="Human-readable summary")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score for extractions")


class ApprovalCreate(ApprovalBase):
    """Schema for creating an approval queue entry."""
    trace_id: Optional[UUID] = Field(None, description="Link to agent trace for observability")


class ApprovalResponse(ApprovalBase):
    """Schema for approval queue response."""
    id: UUID
    proposed_at: datetime
    status: str = Field(..., description="pending, approved, or rejected")
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    result_id: Optional[UUID] = None
    trace_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class ApprovalListResponse(BaseModel):
    """Schema for paginated approval list."""
    items: List[ApprovalResponse]
    total: int
    page: int
    page_size: int


class ApprovalReviewRequest(BaseModel):
    """Schema for approving or rejecting an approval."""
    notes: Optional[str] = Field(None, description="Review notes")


class ApprovalApproveRequest(ApprovalReviewRequest):
    """Schema for approving an approval."""
    pass


class ApprovalRejectRequest(ApprovalReviewRequest):
    """Schema for rejecting an approval."""
    reason: Optional[str] = Field(None, description="Reason for rejection")


# Payload schemas for different action types

class SignalProposalPayload(BaseModel):
    """Payload schema for propose_signal action."""
    pack: str = Field(..., description="Pack name (treasury/wealth)")
    signal_type: str = Field(..., description="Signal type from pack vocabulary")
    payload: Dict[str, Any] = Field(..., description="Signal payload data")
    source: str = Field(..., description="Document source")
    observed_at: datetime
    source_spans: List[Dict[str, Any]] = Field(
        ...,
        description="Source spans showing where in document this was extracted"
    )
    extraction_notes: Optional[str] = Field(None, description="Agent's reasoning")


class SourceSpan(BaseModel):
    """Source span showing where in document data was extracted."""
    start_char: int
    end_char: int
    text: str = Field(..., description="Exact quoted text from document")
    page: Optional[int] = Field(None, description="Page number for PDFs")


class PolicyDraftProposalPayload(BaseModel):
    """Payload schema for propose_policy_draft action."""
    name: str
    description: str
    rule_definition: Dict[str, Any] = Field(..., description="Deterministic rule definition")
    signal_types_referenced: List[str] = Field(..., description="Signals this policy evaluates")
    change_reason: str
    draft_notes: Optional[str] = Field(None, description="Agent's reasoning")
    test_scenarios: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Test scenarios showing expected behavior"
    )


class DismissProposalPayload(BaseModel):
    """Payload schema for dismiss_exception action."""
    exception_id: UUID
    reason: str = Field(..., description="Reason for dismissal")
    notes: Optional[str] = None


class ContextProposalPayload(BaseModel):
    """Payload schema for add_exception_context action."""
    exception_id: UUID
    context_key: str
    context_value: Any
    source: str = Field(..., description="Where this context came from")
