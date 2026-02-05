"""
Intake Processing Schemas.

Sprint 3: Request/response models for document intake processing.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Pack(str, Enum):
    """Available domain packs."""
    treasury = "treasury"
    wealth = "wealth"


class IntakeProcessRequest(BaseModel):
    """Request to process a document through the intake agent."""

    document_text: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="Document content to process (50-50,000 characters)"
    )
    pack: Pack = Field(
        ...,
        description="Target pack for signal extraction"
    )
    document_source: Optional[str] = Field(
        None,
        max_length=500,
        description="Source identifier (e.g., 'Q4 Board Meeting', 'CFO Email')"
    )
    document_date: Optional[datetime] = Field(
        None,
        description="Date of the source document. Used as observed_at for extracted signals. Falls back to submission time if not provided."
    )


class SourceSpanResponse(BaseModel):
    """Source span showing where data was extracted."""

    start_char: int = Field(..., description="Start character offset")
    end_char: int = Field(..., description="End character offset")
    text: str = Field(..., description="Exact quoted text from document")
    page: Optional[int] = Field(None, description="Page number (for PDFs)")


class ExtractedSignalResponse(BaseModel):
    """A signal extracted by the intake agent."""

    signal_type: str = Field(..., description="Signal type from pack vocabulary")
    payload: Dict[str, Any] = Field(..., description="Extracted signal data")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    source_spans: List[SourceSpanResponse] = Field(..., description="Source references")
    extraction_notes: Optional[str] = Field(None, description="Agent's reasoning")
    requires_verification: bool = Field(..., description="True if confidence < 0.7")


class CanonicalizationMetrics(BaseModel):
    """Metrics from the Canonicalizer pass (if enabled)."""

    enabled: bool = Field(False, description="Whether canonicalization was applied")
    breach_count: int = Field(0, description="Signals classified as complete breaches")
    observation_count: int = Field(0, description="Signals downgraded to observations")
    dropped_count: int = Field(0, description="Signals dropped (no constraint match)")
    merged_count: int = Field(0, description="Signals merged as duplicates")
    downgrade_count: int = Field(0, description="Breach candidates downgraded due to incompleteness")
    lookthrough_blocked_count: int = Field(0, description="Signals blocked by missing lookthrough data")


class IntakeProcessResponse(BaseModel):
    """Response from intake processing."""

    trace_id: str = Field(..., description="Agent trace ID for observability")
    signals: List[ExtractedSignalResponse] = Field(
        default_factory=list,
        description="Extracted signals"
    )
    approval_ids: List[str] = Field(
        default_factory=list,
        description="UUIDs of created approval queue entries"
    )
    total_candidates: int = Field(..., description="Total signals extracted")
    high_confidence: int = Field(..., description="Count of high-confidence signals (>= 0.9)")
    requires_verification: int = Field(..., description="Count requiring review (< 0.7)")
    processing_time_ms: int = Field(..., description="Processing duration in milliseconds")
    extraction_notes: Optional[str] = Field(None, description="Overall extraction notes")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")
    canonicalization: Optional[CanonicalizationMetrics] = Field(
        None, description="Canonicalization metrics (present when canonicalization is enabled)"
    )
