"""
Pydantic schemas for Evidence Pack API.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel


class EvidencePackResponse(BaseModel):
    """Schema for evidence pack response."""
    id: UUID
    decision_id: UUID
    evidence: Dict[str, Any]
    content_hash: str
    generated_at: datetime
    narrative_memo: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class NarrativeMemoResponse(BaseModel):
    """Schema for narrative memo only response."""
    decision_id: str
    title: str
    sections: list
    template_used: Optional[str] = None
    length: Optional[str] = None
    pack: Optional[str] = None
    uncertainties: Optional[list] = None
    assumptions: Optional[list] = None
    generated_at: Optional[str] = None
