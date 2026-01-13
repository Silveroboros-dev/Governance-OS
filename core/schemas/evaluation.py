"""
Pydantic schemas for Evaluation API.
"""

from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationTrigger(BaseModel):
    """Schema for triggering evaluation."""
    pack: str = Field(..., description="Pack to evaluate (e.g., 'treasury')")
    trigger: str = Field(default="manual", description="Trigger type: manual, new_signals")
    replay_namespace: str = Field(default="production", description="Replay namespace")


class EvaluationResponse(BaseModel):
    """Schema for evaluation response."""
    id: UUID
    policy_version_id: UUID
    signal_ids: List[UUID]
    result: str
    details: Dict[str, Any]
    input_hash: str
    evaluated_at: datetime
    replay_namespace: str

    class Config:
        from_attributes = True
