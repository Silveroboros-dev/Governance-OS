"""
Coprocessor Schemas - Data models for AI agent outputs.

All AI outputs are schema-validated before use.
"""

from .narrative import (
    NarrativeMemo,
    NarrativeClaim,
    EvidenceReference,
    MemoSection,
)

from .extraction import (
    SourceSpan,
    CandidateSignal,
    ExtractionResult,
    ExtractionValidationResult,
    # Conflict detection
    Conflict,
    ConflictType,
    ConflictFlag,
    ConflictClaim,
    # Drop tracking
    Drop,
    DropReason,
    # Utilities
    validate_signal_type_for_pack,
    get_valid_signal_types,
    PACK_SIGNAL_TYPES,
)

__all__ = [
    # Narrative
    "NarrativeMemo",
    "NarrativeClaim",
    "EvidenceReference",
    "MemoSection",
    # Extraction
    "SourceSpan",
    "CandidateSignal",
    "ExtractionResult",
    "ExtractionValidationResult",
    # Conflict detection
    "Conflict",
    "ConflictType",
    "ConflictFlag",
    "ConflictClaim",
    # Drop tracking
    "Drop",
    "DropReason",
    # Utilities
    "validate_signal_type_for_pack",
    "get_valid_signal_types",
    "PACK_SIGNAL_TYPES",
]
