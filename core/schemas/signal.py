"""
Pydantic schemas for Signal API.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class SignalCreate(BaseModel):
    """Schema for creating a signal."""
    pack: str = Field(..., description="Pack name (e.g., 'treasury')")
    signal_type: str = Field(..., description="Signal type (e.g., 'position_limit_breach')")
    payload: Dict[str, Any] = Field(..., description="Signal payload data")
    source: str = Field(..., description="Signal source (e.g., 'bloomberg_api')")
    reliability: str = Field(..., description="Signal reliability: high, medium, low, unverified")
    observed_at: datetime = Field(..., description="When the signal was observed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SignalResponse(BaseModel):
    """Schema for signal response."""
    id: UUID
    pack: str
    signal_type: str
    payload: Dict[str, Any]
    source: str
    reliability: str
    observed_at: datetime
    ingested_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
