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


class EvaluationSummary(BaseModel):
    """Evaluation data for exception detail."""
    id: UUID
    result: str
    details: Dict[str, Any]
    evaluated_at: datetime
    input_hash: str

    class Config:
        from_attributes = True


class PolicySummary(BaseModel):
    """Policy data for exception detail."""
    id: UUID
    name: str
    pack: str
    description: Optional[str] = None
    version_number: int
    rule_type: Optional[str] = None

    class Config:
        from_attributes = True


class SignalSummary(BaseModel):
    """Signal data for exception detail."""
    id: UUID
    signal_type: str
    payload: Dict[str, Any]
    source: str
    reliability: str
    observed_at: datetime

    class Config:
        from_attributes = True


class ExceptionDetail(BaseModel):
    """
    Schema for full exception detail.

    Includes all related data needed for one-screen decision UI:
    - Exception metadata
    - Evaluation that triggered the exception
    - Policy that was evaluated
    - Signals that contributed to the evaluation
    """
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

    # Related data for decision UI
    evaluation: Optional[EvaluationSummary] = None
    policy: Optional[PolicySummary] = None
    signals: List[SignalSummary] = []

    class Config:
        from_attributes = True
