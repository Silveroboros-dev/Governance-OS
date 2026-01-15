"""
Narrative Schemas - Data models for narrative memos.

All narrative outputs are structured and validated to ensure
proper grounding to evidence.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class MemoLength(str, Enum):
    """Length variants for memo generation."""
    SHORT = "short"      # 1-2 paragraphs, key facts only
    STANDARD = "standard"  # Full narrative, typical length
    DETAILED = "detailed"  # Comprehensive with all context


class MemoTemplate(str, Enum):
    """Available memo templates."""
    # Generic templates
    EXECUTIVE_SUMMARY = "executive_summary"
    DECISION_BRIEF = "decision_brief"

    # Treasury-specific templates
    TREASURY_LIQUIDITY = "treasury_liquidity"
    TREASURY_POSITION = "treasury_position"
    TREASURY_COUNTERPARTY = "treasury_counterparty"

    # Wealth-specific templates
    WEALTH_SUITABILITY = "wealth_suitability"
    WEALTH_PORTFOLIO = "wealth_portfolio"
    WEALTH_CLIENT = "wealth_client"


class MemoTemplateConfig(BaseModel):
    """Configuration for a memo template."""

    template_id: MemoTemplate = Field(..., description="Template identifier")
    name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="What this template is for")
    pack: Optional[str] = Field(default=None, description="Pack this template belongs to (treasury/wealth/None for generic)")

    # Structure configuration
    required_sections: List[str] = Field(
        default_factory=list,
        description="Section headings that must be present"
    )
    max_sections: int = Field(default=5, description="Maximum number of sections")
    max_claims_per_section: int = Field(default=10, description="Maximum claims per section")

    # Length guidelines per MemoLength
    length_guidelines: Dict[str, Dict[str, int]] = Field(
        default_factory=lambda: {
            "short": {"max_sections": 2, "max_claims_per_section": 3},
            "standard": {"max_sections": 4, "max_claims_per_section": 6},
            "detailed": {"max_sections": 6, "max_claims_per_section": 10},
        }
    )

    # Content guidance
    focus_areas: List[str] = Field(
        default_factory=list,
        description="Key areas to emphasize in this template"
    )
    vocabulary_hints: List[str] = Field(
        default_factory=list,
        description="Domain-specific terms to use"
    )


class EvidenceReference(BaseModel):
    """Reference to a piece of evidence supporting a claim."""

    evidence_id: str = Field(..., description="ID of the evidence item (e.g., sig_abc123)")
    evidence_type: str = Field(default="unknown", description="Type of evidence (signal, evaluation, etc.)")
    excerpt: Optional[str] = Field(default=None, description="Brief excerpt from the evidence")

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, v: str) -> str:
        """Ensure evidence_id is not empty."""
        if not v or not v.strip():
            raise ValueError("evidence_id cannot be empty")
        return v.strip()


class NarrativeClaim(BaseModel):
    """
    A single claim in a narrative memo.

    CRITICAL: evidence_refs must not be empty. Every claim
    must be grounded to at least one piece of evidence.
    """

    text: str = Field(..., description="The claim text")
    evidence_refs: List[EvidenceReference] = Field(
        ...,
        description="Evidence references supporting this claim (REQUIRED - must not be empty)",
        min_length=1,
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure text is not empty."""
        if not v or not v.strip():
            raise ValueError("Claim text cannot be empty")
        return v.strip()

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(cls, v: List[EvidenceReference]) -> List[EvidenceReference]:
        """Ensure at least one evidence reference exists."""
        if not v:
            raise ValueError("Every claim must have at least one evidence reference (grounding required)")
        return v


class MemoSection(BaseModel):
    """A section of a narrative memo containing related claims."""

    heading: str = Field(..., description="Section heading")
    claims: List[NarrativeClaim] = Field(
        default_factory=list,
        description="Claims in this section"
    )

    @field_validator("heading")
    @classmethod
    def validate_heading(cls, v: str) -> str:
        """Ensure heading is not empty."""
        if not v or not v.strip():
            raise ValueError("Section heading cannot be empty")
        return v.strip()


class NarrativeMemo(BaseModel):
    """
    A complete narrative memo for a decision.

    Structure:
    - title: Brief summary title
    - sections: Organized sections with grounded claims
    - decision_id: Link to the decision
    - evidence_pack_id: Link to the evidence pack used
    - template_used: Which template was applied
    - length: short/standard/detailed
    """

    decision_id: str = Field(..., description="ID of the decision this memo describes")
    title: str = Field(..., description="Brief title summarizing the decision")
    sections: List[MemoSection] = Field(
        default_factory=list,
        description="Organized sections of the memo"
    )
    evidence_pack_id: Optional[str] = Field(
        default=None,
        description="ID of the evidence pack used for grounding"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this memo was generated"
    )

    # v1 additions: template tracking
    template_used: Optional[str] = Field(
        default=None,
        description="Template ID used to generate this memo"
    )
    length: str = Field(
        default="standard",
        description="Length variant: short, standard, or detailed"
    )
    pack: Optional[str] = Field(
        default=None,
        description="Pack context: treasury or wealth"
    )

    # Metadata for uncertainties and assumptions
    uncertainties: List[str] = Field(
        default_factory=list,
        description="Explicit list of uncertainties in the evidence"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made in the narrative"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v or not v.strip():
            raise ValueError("Memo title cannot be empty")
        return v.strip()

    def get_all_claims(self) -> List[NarrativeClaim]:
        """Get all claims across all sections."""
        claims = []
        for section in self.sections:
            claims.extend(section.claims)
        return claims

    def get_all_evidence_ids(self) -> List[str]:
        """Get all unique evidence IDs referenced in the memo."""
        evidence_ids = set()
        for claim in self.get_all_claims():
            for ref in claim.evidence_refs:
                evidence_ids.add(ref.evidence_id)
        return list(evidence_ids)

    def count_claims(self) -> int:
        """Count total number of claims in the memo."""
        return sum(len(section.claims) for section in self.sections)

    def is_fully_grounded(self) -> bool:
        """Check if all claims have evidence references."""
        for claim in self.get_all_claims():
            if not claim.evidence_refs:
                return False
        return True


class NarrativeValidationResult(BaseModel):
    """Result of validating a narrative memo."""

    is_valid: bool = Field(..., description="Whether the memo passed validation")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    claims_checked: int = Field(default=0, description="Number of claims validated")
    evidence_refs_checked: int = Field(default=0, description="Number of evidence refs validated")

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)
