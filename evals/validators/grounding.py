"""
Grounding Validator - Ensures all claims are properly grounded to evidence.

CRITICAL: Every claim in a narrative memo must reference at least one
valid evidence ID from the evidence pack. This is a non-negotiable
requirement for AI outputs in Governance OS.
"""

from typing import Any, Dict, List, Set

from pydantic import BaseModel, Field

from coprocessor.schemas.narrative import NarrativeMemo, NarrativeClaim


class UngroundedClaimError(BaseModel):
    """Error for a claim without evidence references."""

    claim_text: str
    section: str
    error_type: str = "ungrounded_claim"
    message: str = Field(default="")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.message:
            self.message = f"Claim has no evidence references: '{self.claim_text[:50]}...'"


class InvalidEvidenceRefError(BaseModel):
    """Error for an evidence reference that doesn't exist in the pack."""

    evidence_id: str
    claim_text: str
    section: str
    error_type: str = "invalid_evidence_ref"
    message: str = Field(default="")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.message:
            self.message = f"Evidence ID '{self.evidence_id}' not found in evidence pack"


class GroundingResult(BaseModel):
    """Result of grounding validation."""

    passed: bool
    total_claims: int = 0
    grounded_claims: int = 0
    total_evidence_refs: int = 0
    valid_evidence_refs: int = 0
    errors: List[Any] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @property
    def grounding_rate(self) -> float:
        """Percentage of claims that are properly grounded."""
        if self.total_claims == 0:
            return 100.0
        return (self.grounded_claims / self.total_claims) * 100

    @property
    def evidence_validity_rate(self) -> float:
        """Percentage of evidence refs that are valid."""
        if self.total_evidence_refs == 0:
            return 100.0
        return (self.valid_evidence_refs / self.total_evidence_refs) * 100


class GroundingValidator:
    """
    Validates that all claims in a narrative memo are grounded to evidence.

    Rules:
    1. Every claim MUST have at least one evidence reference
    2. Every evidence reference MUST exist in the evidence pack
    3. Evidence IDs must exactly match (case-sensitive)
    """

    def __init__(self, strict: bool = True):
        """
        Initialize the validator.

        Args:
            strict: If True, any error fails validation. If False, only
                   ungrounded claims fail (invalid refs become warnings).
        """
        self.strict = strict

    def validate(
        self,
        memo: NarrativeMemo,
        evidence_pack: Dict[str, Any],
    ) -> GroundingResult:
        """
        Validate grounding of all claims in the memo.

        Args:
            memo: The narrative memo to validate
            evidence_pack: The evidence pack for reference validation

        Returns:
            GroundingResult with validation status and errors
        """
        result = GroundingResult(passed=True)

        # Extract available evidence IDs
        available_ids = self._extract_evidence_ids(evidence_pack)

        # Validate each section and claim
        for section in memo.sections:
            for claim in section.claims:
                result.total_claims += 1

                # Check 1: Claim has evidence references
                if not claim.evidence_refs:
                    result.errors.append(UngroundedClaimError(
                        claim_text=claim.text,
                        section=section.heading,
                    ))
                    result.passed = False
                    continue

                # Claim has refs, count as grounded (for now)
                claim_valid = True

                # Check 2: All evidence refs exist
                for ref in claim.evidence_refs:
                    result.total_evidence_refs += 1

                    if ref.evidence_id in available_ids:
                        result.valid_evidence_refs += 1
                    else:
                        error = InvalidEvidenceRefError(
                            evidence_id=ref.evidence_id,
                            claim_text=claim.text,
                            section=section.heading,
                        )

                        if self.strict:
                            result.errors.append(error)
                            result.passed = False
                            claim_valid = False
                        else:
                            result.warnings.append(error.message)

                if claim_valid:
                    result.grounded_claims += 1

        return result

    def _extract_evidence_ids(self, evidence_pack: Dict[str, Any]) -> Set[str]:
        """Extract all evidence IDs from the pack."""
        ids = set()

        # From evidence_items list
        for item in evidence_pack.get("evidence_items", []):
            if eid := item.get("evidence_id"):
                ids.add(eid)

        return ids

    def validate_claim(
        self,
        claim: NarrativeClaim,
        available_ids: Set[str],
    ) -> List[str]:
        """
        Validate a single claim.

        Args:
            claim: The claim to validate
            available_ids: Set of valid evidence IDs

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not claim.evidence_refs:
            errors.append(f"Ungrounded claim: '{claim.text[:50]}...'")
            return errors

        for ref in claim.evidence_refs:
            if ref.evidence_id not in available_ids:
                errors.append(f"Invalid evidence ref: '{ref.evidence_id}'")

        return errors


def validate_grounding(
    memo: NarrativeMemo,
    evidence_pack: Dict[str, Any],
    strict: bool = True,
) -> GroundingResult:
    """
    Convenience function to validate memo grounding.

    Args:
        memo: The narrative memo to validate
        evidence_pack: The evidence pack for reference validation
        strict: If True, any error fails validation

    Returns:
        GroundingResult with validation status
    """
    validator = GroundingValidator(strict=strict)
    return validator.validate(memo, evidence_pack)
