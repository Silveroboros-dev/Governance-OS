"""
Pydantic schemas for Exception API.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ExceptionOption(BaseModel):
    """Schema for exception option."""
    id: str
    label: str
    description: str
    implications: List[str]


class ExceptionListItem(BaseModel):
    """Schema for exception in list view."""
    id: UUID
    title: str
    severity: str
    status: str
    raised_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExceptionDetail(BaseModel):
    """Schema for full exception detail."""
    id: UUID
    evaluation_id: UUID
    fingerprint: str
    severity: str
    status: str
    title: str
    context: Dict[str, Any]
    options: List[Dict[str, Any]]  # List of ExceptionOption dicts
    raised_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True
