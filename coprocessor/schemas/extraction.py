"""
Extraction Schemas - Data models for signal extraction from documents.

Sprint 3: IntakeAgent extracts candidate signals from unstructured documents.

Enhanced with concepts from Signal Compiler:
- Conflicts: When multiple sources disagree on the same fact
- Drops: Signals that couldn't be extracted (with reason)
- BBox support: Visual grounding for PDFs/scans
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator


class SourceSpan(BaseModel):
    """
    Source span showing where in document data was extracted.

    Every extracted value must have at least one source span
    pointing to the exact text it was derived from.

    For PDFs/scans, bbox provides visual grounding coordinates.
    """

    start_char: int = Field(default=0, ge=0, description="Start character offset in document")
    end_char: int = Field(default=0, ge=0, description="End character offset in document")
    text: str = Field(..., description="Exact quoted text from document")
    page: Optional[int] = Field(None, ge=1, description="Page number (for PDFs)")
    bbox: Optional[Tuple[float, float, float, float]] = Field(
        None,
        description="Bounding box for scans [x, y, width, height] normalized 0-1"
    )
    doc_id: Optional[str] = Field(
        None,
        description="Document identifier (for multi-document extraction)"
    )

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

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: Optional[Tuple[float, float, float, float]]) -> Optional[Tuple[float, float, float, float]]:
        """Validate bbox coordinates are in 0-1 range."""
        if v is not None:
            if len(v) != 4:
                raise ValueError("bbox must have exactly 4 values [x, y, width, height]")
            if not all(0 <= coord <= 1 for coord in v):
                raise ValueError("bbox coordinates must be normalized to 0-1 range")
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


# =============================================================================
# Drop Schema - Tracking what couldn't be extracted
# =============================================================================

class DropReason(str, Enum):
    """Canonical reasons why a signal couldn't be extracted."""
    MISSING_EVIDENCE = "missing_evidence"  # Mentioned but no supporting quote
    AMBIGUOUS = "ambiguous"  # Multiple interpretations possible
    REFERENCED_NOT_ATTACHED = "referenced_not_attached"  # Document mentioned but not provided
    LOW_CONFIDENCE = "low_confidence"  # Confidence too low to include
    INVALID_SIGNAL_TYPE = "invalid_signal_type"  # Not in pack vocabulary
    INCOMPLETE_DATA = "incomplete_data"  # Missing required fields


class Drop(BaseModel):
    """
    A signal that couldn't be extracted, with explanation.

    Drops provide transparency about extraction limitations and
    guide users on what additional input would help.
    """

    id: str = Field(..., description="Unique drop identifier (e.g., 'D1')")
    what: str = Field(..., description="What we tried to extract")
    reason: DropReason = Field(..., description="Why extraction failed")
    detail: str = Field(..., description="Human-readable explanation")
    would_fix: str = Field(..., description="What input would resolve this")
    source_hint: Optional[str] = Field(
        None,
        description="Where the reference was found (doc_id, page)"
    )


# =============================================================================
# Conflict Schema - When sources disagree
# =============================================================================

class ConflictType(str, Enum):
    """Canonical conflict taxonomy - stable across domains."""
    # Liquidity conflicts
    CASH_DEFINITION = "liquidity.cash_definition"  # Different cash definitions
    CASH_AMOUNT = "liquidity.cash_amount"  # Same definition, different amounts

    # Logistics conflicts
    ETA = "logistics.eta"  # Delivery time discrepancies
    QUANTITY = "logistics.quantity"  # Shipped vs received quantities

    # Quality conflicts
    CONFORMANCE = "quality.conformance"  # Pass vs fail on same spec

    # Financial conflicts
    PAYMENT_TERMS = "sales.payment_terms"  # Disputed payment terms
    VALUATION = "valuation.amount"  # Different valuations for same asset

    # Operational conflicts
    INVENTORY_COUNT = "ops.inventory_count"  # Inventory discrepancies
    POSITION = "position.amount"  # Position size disagreements


class ConflictFlag(str, Enum):
    """Flags that indicate conflict severity or characteristics."""
    VALUE_DATE_MISMATCH = "value_date_mismatch"  # Claims have different as-of dates
    DEFINITION_UNKNOWN = "definition_unknown"  # One or more claims has unclear definition
    BLOCKER = "blocker"  # This conflict blocks downstream calculations
    MATERIAL = "material"  # Difference exceeds materiality threshold


class ConflictClaim(BaseModel):
    """A single claim within a conflict - one source's assertion."""

    source: str = Field(..., description="Document or source identifier")
    value: str = Field(..., description="The claimed value")
    quote: str = Field(..., description="Exact quote from source")
    page: Optional[int] = Field(None, description="Page number")
    definition: Optional[str] = Field(
        None,
        description="Value definition (e.g., 'ledger', 'available', 'unrestricted')"
    )
    value_date: Optional[str] = Field(
        None,
        description="As-of date for this value (ISO format)"
    )
    bbox: Optional[Tuple[float, float, float, float]] = Field(
        None,
        description="Bounding box for visual grounding"
    )


class Conflict(BaseModel):
    """
    A conflict where multiple sources disagree on the same fact.

    Conflicts are first-class objects because disagreement between
    sources is a critical signal for human review.
    """

    id: str = Field(..., description="Unique conflict identifier (e.g., 'C1')")
    conflict_type: ConflictType = Field(..., description="Canonical conflict type")
    topic: str = Field(..., description="Human-readable topic (e.g., 'Cash Position')")
    claims: List[ConflictClaim] = Field(
        ...,
        min_length=2,
        description="Conflicting claims from different sources"
    )
    flags: List[ConflictFlag] = Field(
        default_factory=list,
        description="Flags indicating conflict characteristics"
    )
    how_to_resolve: str = Field(..., description="Recommended resolution approach")
    blocker_for: List[str] = Field(
        default_factory=list,
        description="Signal IDs that are blocked by this conflict"
    )

    @property
    def is_blocker(self) -> bool:
        """Check if this conflict blocks other calculations."""
        return ConflictFlag.BLOCKER in self.flags

    @property
    def has_date_mismatch(self) -> bool:
        """Check if claims have different value dates."""
        return ConflictFlag.VALUE_DATE_MISMATCH in self.flags

    @property
    def claim_count(self) -> int:
        """Number of conflicting claims."""
        return len(self.claims)


class ExtractionResult(BaseModel):
    """
    Result of extracting signals from a document.

    Contains:
    - candidates: Signals extracted successfully
    - conflicts: When sources disagree on the same fact
    - drops: Signals that couldn't be extracted (with reason)
    - thinking_summary: Gemini's reasoning chain (Thinking Mode)
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
    conflicts: List[Conflict] = Field(
        default_factory=list,
        description="Conflicts where sources disagree"
    )
    drops: List[Drop] = Field(
        default_factory=list,
        description="Signals that couldn't be extracted"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Overall notes about the extraction"
    )
    thinking_summary: Optional[str] = Field(
        None,
        description="Gemini's reasoning chain for the extraction (Thinking Mode)"
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

    @property
    def conflict_count(self) -> int:
        """Count conflicts detected."""
        return len(self.conflicts)

    @property
    def blocking_conflict_count(self) -> int:
        """Count conflicts that block downstream calculations."""
        return sum(1 for c in self.conflicts if c.is_blocker)

    @property
    def drop_count(self) -> int:
        """Count signals that couldn't be extracted."""
        return len(self.drops)

    def get_candidates_by_type(self, signal_type: str) -> List[CandidateSignal]:
        """Get candidates of a specific type."""
        return [c for c in self.candidates if c.signal_type == signal_type]

    def get_conflicts_by_type(self, conflict_type: ConflictType) -> List[Conflict]:
        """Get conflicts of a specific type."""
        return [c for c in self.conflicts if c.conflict_type == conflict_type]

    def get_blocking_conflicts(self) -> List[Conflict]:
        """Get conflicts that block downstream calculations."""
        return [c for c in self.conflicts if c.is_blocker]

    def get_drops_by_reason(self, reason: DropReason) -> List[Drop]:
        """Get drops with a specific reason."""
        return [d for d in self.drops if d.reason == reason]


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
