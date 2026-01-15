"""
Pydantic schemas for Agent Trace API.

Sprint 3: Schemas for agent execution observability.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class ToolCallSchema(BaseModel):
    """Schema for a single tool call within a trace."""
    tool: str = Field(..., description="Tool name that was called")
    args: Dict[str, Any] = Field(..., description="Arguments passed to tool")
    result: Any = Field(..., description="Result returned by tool")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    timestamp: datetime
    error: Optional[str] = Field(None, description="Error message if call failed")


class TraceBase(BaseModel):
    """Base schema for agent traces."""
    agent_type: str = Field(..., description="Agent type: intake, narrative, policy_draft")
    session_id: UUID
    pack: Optional[str] = Field(None, description="Pack name (treasury/wealth)")
    document_source: Optional[str] = Field(None, description="Document source for intake agent")


class TraceCreate(TraceBase):
    """Schema for creating an agent trace."""
    input_summary: Optional[Dict[str, Any]] = None


class TraceResponse(TraceBase):
    """Schema for agent trace response."""
    id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = Field(..., description="running, completed, or failed")
    input_summary: Optional[Dict[str, Any]] = None
    output_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    total_duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class TraceDetailResponse(TraceResponse):
    """Detailed trace response including tool calls."""
    tool_calls: Optional[List[ToolCallSchema]] = None
    approval_count: int = Field(0, description="Number of approvals created by this trace")


class TraceListResponse(BaseModel):
    """Schema for paginated trace list."""
    items: List[TraceResponse]
    total: int
    page: int
    page_size: int


class TraceToolCallsResponse(BaseModel):
    """Schema for trace tool calls endpoint."""
    trace_id: UUID
    tool_calls: List[ToolCallSchema]
    total_calls: int


class TraceUpdateRequest(BaseModel):
    """Schema for updating a trace (adding tool calls, completing, etc.)."""
    tool_call: Optional[ToolCallSchema] = Field(None, description="Add a tool call")
    status: Optional[str] = Field(None, description="Update status")
    output_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class TraceCompleteRequest(BaseModel):
    """Schema for marking a trace as complete."""
    output_summary: Optional[Dict[str, Any]] = None


class TraceFailRequest(BaseModel):
    """Schema for marking a trace as failed."""
    error_message: str
