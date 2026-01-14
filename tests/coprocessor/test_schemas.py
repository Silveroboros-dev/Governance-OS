"""
Tests for Coprocessor Schemas - Narrative memo data models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from coprocessor.schemas.narrative import (
    EvidenceReference,
    NarrativeClaim,
    MemoSection,
    NarrativeMemo,
    NarrativeValidationResult,
)


class TestEvidenceReference:
    """Tests for EvidenceReference model."""

    def test_valid_evidence_reference(self):
        """Test creating a valid evidence reference."""
        ref = EvidenceReference(
            evidence_id="sig_001",
            evidence_type="signal",
            excerpt="Position breach detected",
        )

        assert ref.evidence_id == "sig_001"
        assert ref.evidence_type == "signal"
        assert ref.excerpt == "Position breach detected"

    def test_evidence_reference_minimal(self):
        """Test minimal evidence reference (only required fields)."""
        ref = EvidenceReference(evidence_id="sig_001")

        assert ref.evidence_id == "sig_001"
        assert ref.evidence_type == "unknown"
        assert ref.excerpt is None

    def test_evidence_reference_empty_id_fails(self):
        """Test that empty evidence_id fails validation."""
        with pytest.raises(ValidationError):
            EvidenceReference(evidence_id="")

        with pytest.raises(ValidationError):
            EvidenceReference(evidence_id="   ")

    def test_evidence_reference_id_stripped(self):
        """Test that evidence_id is stripped of whitespace."""
        ref = EvidenceReference(evidence_id="  sig_001  ")
        assert ref.evidence_id == "sig_001"


class TestNarrativeClaim:
    """Tests for NarrativeClaim model."""

    def test_valid_claim(self):
        """Test creating a valid claim with evidence."""
        claim = NarrativeClaim(
            text="The position exceeded the limit",
            evidence_refs=[
                EvidenceReference(evidence_id="sig_001", evidence_type="signal"),
            ],
        )

        assert claim.text == "The position exceeded the limit"
        assert len(claim.evidence_refs) == 1

    def test_claim_multiple_evidence(self):
        """Test claim with multiple evidence references."""
        claim = NarrativeClaim(
            text="Based on multiple sources",
            evidence_refs=[
                EvidenceReference(evidence_id="sig_001"),
                EvidenceReference(evidence_id="eval_001"),
                EvidenceReference(evidence_id="pol_001"),
            ],
        )

        assert len(claim.evidence_refs) == 3

    def test_claim_empty_text_fails(self):
        """Test that empty claim text fails validation."""
        with pytest.raises(ValidationError):
            NarrativeClaim(
                text="",
                evidence_refs=[EvidenceReference(evidence_id="sig_001")],
            )

    def test_claim_empty_evidence_refs_fails(self):
        """Test that empty evidence_refs fails validation (grounding required)."""
        with pytest.raises(ValidationError) as exc_info:
            NarrativeClaim(
                text="This claim has no evidence",
                evidence_refs=[],
            )

        # Should mention grounding requirement
        assert "evidence" in str(exc_info.value).lower()

    def test_claim_no_evidence_refs_fails(self):
        """Test that missing evidence_refs fails validation."""
        with pytest.raises(ValidationError):
            NarrativeClaim(text="This claim has no evidence")

    def test_claim_text_stripped(self):
        """Test that claim text is stripped."""
        claim = NarrativeClaim(
            text="  Whitespace around text  ",
            evidence_refs=[EvidenceReference(evidence_id="sig_001")],
        )
        assert claim.text == "Whitespace around text"


class TestMemoSection:
    """Tests for MemoSection model."""

    def test_valid_section(self):
        """Test creating a valid section."""
        section = MemoSection(
            heading="Situation",
            claims=[
                NarrativeClaim(
                    text="Position exceeded limit",
                    evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                ),
            ],
        )

        assert section.heading == "Situation"
        assert len(section.claims) == 1

    def test_section_empty_claims_allowed(self):
        """Test that section with no claims is allowed."""
        section = MemoSection(
            heading="Empty Section",
            claims=[],
        )

        assert section.heading == "Empty Section"
        assert len(section.claims) == 0

    def test_section_empty_heading_fails(self):
        """Test that empty heading fails validation."""
        with pytest.raises(ValidationError):
            MemoSection(heading="", claims=[])

    def test_section_heading_stripped(self):
        """Test that heading is stripped."""
        section = MemoSection(heading="  Situation  ", claims=[])
        assert section.heading == "Situation"


class TestNarrativeMemo:
    """Tests for NarrativeMemo model."""

    def test_valid_memo(self, sample_grounded_memo_data):
        """Test creating a valid memo."""
        # Build sections from fixture data
        sections = []
        for section_data in sample_grounded_memo_data["sections"]:
            claims = []
            for claim_data in section_data["claims"]:
                refs = [
                    EvidenceReference(**ref)
                    for ref in claim_data["evidence_refs"]
                ]
                claims.append(NarrativeClaim(
                    text=claim_data["text"],
                    evidence_refs=refs,
                ))
            sections.append(MemoSection(
                heading=section_data["heading"],
                claims=claims,
            ))

        memo = NarrativeMemo(
            decision_id=sample_grounded_memo_data["decision_id"],
            title=sample_grounded_memo_data["title"],
            sections=sections,
        )

        assert memo.decision_id == "dec_001"
        assert memo.title == "Position Limit Breach Resolution"
        assert len(memo.sections) == 2

    def test_memo_empty_title_fails(self):
        """Test that empty title fails validation."""
        with pytest.raises(ValidationError):
            NarrativeMemo(
                decision_id="dec_001",
                title="",
                sections=[],
            )

    def test_memo_generated_at_default(self):
        """Test that generated_at defaults to now."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test Memo",
            sections=[],
        )

        assert memo.generated_at is not None
        assert isinstance(memo.generated_at, datetime)

    def test_get_all_claims(self):
        """Test getting all claims across sections."""
        sections = [
            MemoSection(
                heading="Section 1",
                claims=[
                    NarrativeClaim(text="Claim 1", evidence_refs=[EvidenceReference(evidence_id="e1")]),
                    NarrativeClaim(text="Claim 2", evidence_refs=[EvidenceReference(evidence_id="e2")]),
                ],
            ),
            MemoSection(
                heading="Section 2",
                claims=[
                    NarrativeClaim(text="Claim 3", evidence_refs=[EvidenceReference(evidence_id="e3")]),
                ],
            ),
        ]

        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=sections,
        )

        all_claims = memo.get_all_claims()
        assert len(all_claims) == 3

    def test_get_all_evidence_ids(self):
        """Test getting unique evidence IDs."""
        sections = [
            MemoSection(
                heading="Section 1",
                claims=[
                    NarrativeClaim(
                        text="Claim 1",
                        evidence_refs=[
                            EvidenceReference(evidence_id="e1"),
                            EvidenceReference(evidence_id="e2"),
                        ],
                    ),
                    NarrativeClaim(
                        text="Claim 2",
                        evidence_refs=[
                            EvidenceReference(evidence_id="e2"),  # Duplicate
                            EvidenceReference(evidence_id="e3"),
                        ],
                    ),
                ],
            ),
        ]

        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=sections,
        )

        evidence_ids = memo.get_all_evidence_ids()
        assert len(evidence_ids) == 3
        assert set(evidence_ids) == {"e1", "e2", "e3"}

    def test_count_claims(self):
        """Test counting total claims."""
        sections = [
            MemoSection(heading="S1", claims=[
                NarrativeClaim(text="C1", evidence_refs=[EvidenceReference(evidence_id="e1")]),
                NarrativeClaim(text="C2", evidence_refs=[EvidenceReference(evidence_id="e2")]),
            ]),
            MemoSection(heading="S2", claims=[]),  # Empty section
            MemoSection(heading="S3", claims=[
                NarrativeClaim(text="C3", evidence_refs=[EvidenceReference(evidence_id="e3")]),
            ]),
        ]

        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=sections,
        )

        assert memo.count_claims() == 3

    def test_is_fully_grounded(self):
        """Test checking if memo is fully grounded."""
        # All claims have evidence
        sections = [
            MemoSection(heading="S1", claims=[
                NarrativeClaim(text="C1", evidence_refs=[EvidenceReference(evidence_id="e1")]),
            ]),
        ]

        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=sections,
        )

        assert memo.is_fully_grounded() is True

    def test_empty_memo_is_grounded(self):
        """Test that empty memo is considered grounded."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Empty Memo",
            sections=[],
        )

        assert memo.is_fully_grounded() is True


class TestNarrativeValidationResult:
    """Tests for NarrativeValidationResult model."""

    def test_validation_result_properties(self):
        """Test validation result calculated properties."""
        result = NarrativeValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            claims_checked=10,
            evidence_refs_checked=25,
        )

        assert result.error_count == 2
        assert result.warning_count == 1

    def test_validation_result_valid(self):
        """Test valid validation result."""
        result = NarrativeValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            claims_checked=5,
            evidence_refs_checked=12,
        )

        assert result.is_valid is True
        assert result.error_count == 0
