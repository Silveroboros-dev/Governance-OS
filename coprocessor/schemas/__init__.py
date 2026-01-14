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

__all__ = [
    "NarrativeMemo",
    "NarrativeClaim",
    "EvidenceReference",
    "MemoSection",
]
