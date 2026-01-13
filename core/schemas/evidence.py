"""
Pydantic schemas for Evidence Pack API.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from pydantic import BaseModel


class EvidencePackResponse(BaseModel):
    """Schema for evidence pack response."""
    id: UUID
    decision_id: UUID
    evidence: Dict[str, Any]
    content_hash: str
    generated_at: datetime

    class Config:
        from_attributes = True
