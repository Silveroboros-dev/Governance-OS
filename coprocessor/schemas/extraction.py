"""
Extraction Schemas - Data models for signal extraction from documents.

Sprint 3: IntakeAgent extracts candidate signals from unstructured documents.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SourceSpan(BaseModel):
    """
    Source span showing where in document data was extracted.

    Every extracted value must have at least one source span
    pointing to the exact text it was derived from.
    """

    start_char: int = Field(..., ge=0, description="Start character offset in document")
    end_char: int = Field(..., ge=0, description="End character offset in document")
    text: str = Field(..., description="Exact quoted text from document")
    page: Optional[int] = Field(None, ge=1, description="Page number (for PDFs)")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure text is not empty."""
        if not v or not v.strip():
            raise ValueError("Source span text cannot be empty")
        return v

    @field_validator("end_char")
    @classmethod
    def validate_end_after_start(cls, v: int, info) -> int:
        """Ensure end is after start."""
        if "start_char" in info.data and v < info.data["start_char"]:
            raise ValueError("end_char must be >= start_char")
        return v


class CandidateSignal(BaseModel):
    """
    A candidate signal extracted from a document.

    SAFETY INVARIANTS:
    - signal_type must be from pack vocabulary
    - Every field must have source_span reference
    - Confidence < 0.7 requires human verification
    - Never infer values not explicitly stated
    """

    signal_type: str = Field(
        ...,
        description="Signal type from pack vocabulary (e.g., 'position_limit_breach')"
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Signal payload data extracted from document"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0.0-1.0)"
    )
    source_spans: List[SourceSpan] = Field(
        ...,
        min_length=1,
        description="Source spans showing where data was extracted from"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Agent's reasoning about the extraction"
    )

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, v: str) -> str:
        """Ensure signal_type is not empty."""
        if not v or not v.strip():
            raise ValueError("signal_type cannot be empty")
        return v.strip()

    @property
    def requires_verification(self) -> bool:
        """Check if this extraction requires human verification."""
        return self.confidence < 0.7

    @property
    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence extraction."""
        return self.confidence >= 0.9


class ExtractionResult(BaseModel):
    """
    Result of extracting signals from a document.

    Contains candidate signals for human review via approval queue.
    """

    document_source: str = Field(..., description="Source identifier for the document")
    document_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata (sender, received_at, etc.)"
    )
    pack: str = Field(..., description="Target pack (treasury/wealth)")
    candidates: List[CandidateSignal] = Field(
        default_factory=list,
        description="Candidate signals extracted from document"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Overall notes about the extraction"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When extraction was performed"
    )

    @property
    def total_candidates(self) -> int:
        """Get total number of candidate signals."""
        return len(self.candidates)

    @property
    def high_confidence_count(self) -> int:
        """Count high-confidence extractions."""
        return sum(1 for c in self.candidates if c.is_high_confidence)

    @property
    def requires_verification_count(self) -> int:
        """Count extractions requiring verification."""
        return sum(1 for c in self.candidates if c.requires_verification)

    def get_candidates_by_type(self, signal_type: str) -> List[CandidateSignal]:
        """Get candidates of a specific type."""
        return [c for c in self.candidates if c.signal_type == signal_type]


class ExtractionValidationResult(BaseModel):
    """Result of validating an extraction result."""

    is_valid: bool = Field(..., description="Whether extraction passed validation")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    candidates_checked: int = Field(default=0, description="Number of candidates validated")


# Pack-specific signal type definitions (used for validation)
TREASURY_SIGNAL_TYPES = [
    "position_limit_breach",
    "concentration_threshold",
    "market_volatility_spike",
    "counterparty_exposure_change",
    "counterparty_credit_downgrade",
    "regulatory_filing_received",
    "collateral_margin_call",
    "fx_hedge_expiration",
    "fx_exposure_breach",
    "credit_rating_change",
    "liquidity_threshold_breach",
    "cash_forecast_variance",
    "covenant_breach",
    "settlement_failure",
    "settlement_rail_shortfall",
]

WEALTH_SIGNAL_TYPES = [
    "risk_tolerance_change",
    "large_transaction_alert",
    "beneficiary_update",
    "tax_event",
    "estate_document_update",
    "investment_objective_change",
    "account_ownership_change",
    "compliance_violation_flag",
]

PACK_SIGNAL_TYPES = {
    "treasury": TREASURY_SIGNAL_TYPES,
    "wealth": WEALTH_SIGNAL_TYPES,
}


def validate_signal_type_for_pack(signal_type: str, pack: str) -> bool:
    """Check if a signal type is valid for a pack."""
    if pack not in PACK_SIGNAL_TYPES:
        return False
    return signal_type in PACK_SIGNAL_TYPES[pack]


def get_valid_signal_types(pack: str) -> List[str]:
    """Get valid signal types for a pack."""
    return PACK_SIGNAL_TYPES.get(pack, [])
