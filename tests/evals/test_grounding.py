"""
Tests for Grounding Validator - Ensures all claims are grounded to evidence.
"""

import pytest

from evals.validators.grounding import (
    GroundingValidator,
    GroundingResult,
    UngroundedClaimError,
    InvalidEvidenceRefError,
    validate_grounding,
)
from coprocessor.schemas.narrative import (
    NarrativeMemo,
    NarrativeClaim,
    EvidenceReference,
    MemoSection,
)


class TestGroundingValidator:
    """Tests for GroundingValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a strict grounding validator."""
        return GroundingValidator(strict=True)

    @pytest.fixture
    def non_strict_validator(self):
        """Create a non-strict grounding validator."""
        return GroundingValidator(strict=False)

    @pytest.fixture
    def valid_memo(self):
        """Create a properly grounded memo."""
        sections = [
            MemoSection(
                heading="Situation",
                claims=[
                    NarrativeClaim(
                        text="The position exceeded the limit",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_001", evidence_type="signal"),
                        ],
                    ),
                    NarrativeClaim(
                        text="This triggered a high-severity exception",
                        evidence_refs=[
                            EvidenceReference(evidence_id="exc_001", evidence_type="exception_context"),
                            EvidenceReference(evidence_id="eval_001", evidence_type="evaluation"),
                        ],
                    ),
                ],
            ),
        ]
        return NarrativeMemo(
            decision_id="dec_001",
            title="Test Memo",
            sections=sections,
        )

    @pytest.fixture
    def evidence_pack(self):
        """Create a matching evidence pack."""
        return {
            "evidence_pack_id": "evp_001",
            "evidence_items": [
                {"evidence_id": "sig_001", "type": "signal", "data": {}},
                {"evidence_id": "exc_001", "type": "exception_context", "data": {}},
                {"evidence_id": "eval_001", "type": "evaluation", "data": {}},
            ],
        }

    def test_validate_fully_grounded_memo(self, validator, valid_memo, evidence_pack):
        """Test validation of a fully grounded memo."""
        result = validator.validate(valid_memo, evidence_pack)

        assert result.passed is True
        assert result.total_claims == 2
        assert result.grounded_claims == 2
        assert result.total_evidence_refs == 3
        assert result.valid_evidence_refs == 3
        assert len(result.errors) == 0

    def test_validate_invalid_evidence_ref_strict(self, validator, evidence_pack):
        """Test strict validation fails on invalid evidence reference."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Claim with invalid ref",
                        evidence_refs=[
                            EvidenceReference(evidence_id="nonexistent", evidence_type="unknown"),
                        ],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = validator.validate(memo, evidence_pack)

        assert result.passed is False
        assert result.valid_evidence_refs == 0
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], InvalidEvidenceRefError)

    def test_validate_invalid_evidence_ref_non_strict(self, non_strict_validator, evidence_pack):
        """Test non-strict validation warns on invalid evidence reference."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Claim with invalid ref",
                        evidence_refs=[
                            EvidenceReference(evidence_id="nonexistent", evidence_type="unknown"),
                        ],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = non_strict_validator.validate(memo, evidence_pack)

        # Non-strict mode: invalid ref is a warning, not error
        assert result.passed is True  # Still passes
        assert len(result.warnings) == 1
        assert len(result.errors) == 0

    def test_validate_mixed_valid_invalid_refs(self, validator, evidence_pack):
        """Test memo with mix of valid and invalid references."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Claim with mixed refs",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_001", evidence_type="signal"),
                            EvidenceReference(evidence_id="invalid", evidence_type="unknown"),
                        ],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = validator.validate(memo, evidence_pack)

        assert result.passed is False
        assert result.valid_evidence_refs == 1
        assert result.total_evidence_refs == 2

    def test_grounding_rate_calculation(self, validator, evidence_pack):
        """Test grounding rate is calculated correctly."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Grounded claim",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                    NarrativeClaim(
                        text="Another grounded claim",
                        evidence_refs=[EvidenceReference(evidence_id="exc_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = validator.validate(memo, evidence_pack)

        assert result.grounding_rate == 100.0

    def test_evidence_validity_rate_calculation(self, validator, evidence_pack):
        """Test evidence validity rate calculation."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Claim with one valid, one invalid",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_001"),
                            EvidenceReference(evidence_id="invalid"),
                        ],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = validator.validate(memo, evidence_pack)

        assert result.evidence_validity_rate == 50.0

    def test_empty_memo_passes(self, validator, evidence_pack):
        """Test that empty memo passes validation."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Empty Memo",
            sections=[],
        )

        result = validator.validate(memo, evidence_pack)

        assert result.passed is True
        assert result.grounding_rate == 100.0

    def test_validate_claim_method(self, validator):
        """Test single claim validation."""
        available_ids = {"sig_001", "exc_001"}

        # Valid claim
        claim = NarrativeClaim(
            text="Valid claim",
            evidence_refs=[EvidenceReference(evidence_id="sig_001")],
        )
        errors = validator.validate_claim(claim, available_ids)
        assert len(errors) == 0

        # Claim with invalid ref
        claim = NarrativeClaim(
            text="Invalid claim",
            evidence_refs=[EvidenceReference(evidence_id="invalid")],
        )
        errors = validator.validate_claim(claim, available_ids)
        assert len(errors) == 1

    def test_extract_evidence_ids(self, validator):
        """Test evidence ID extraction from pack."""
        pack = {
            "evidence_items": [
                {"evidence_id": "sig_001"},
                {"evidence_id": "exc_001"},
                {"evidence_id": "eval_001"},
            ]
        }

        ids = validator._extract_evidence_ids(pack)

        assert len(ids) == 3
        assert "sig_001" in ids
        assert "exc_001" in ids
        assert "eval_001" in ids

    def test_extract_evidence_ids_empty_pack(self, validator):
        """Test extraction from empty pack."""
        pack = {"evidence_items": []}
        ids = validator._extract_evidence_ids(pack)
        assert len(ids) == 0

        pack = {}
        ids = validator._extract_evidence_ids(pack)
        assert len(ids) == 0


class TestGroundingResult:
    """Tests for GroundingResult model."""

    def test_grounding_rate_zero_claims(self):
        """Test grounding rate with zero claims."""
        result = GroundingResult(
            passed=True,
            total_claims=0,
            grounded_claims=0,
        )
        assert result.grounding_rate == 100.0

    def test_evidence_validity_rate_zero_refs(self):
        """Test evidence validity rate with zero refs."""
        result = GroundingResult(
            passed=True,
            total_evidence_refs=0,
            valid_evidence_refs=0,
        )
        assert result.evidence_validity_rate == 100.0


class TestUngroundedClaimError:
    """Tests for UngroundedClaimError model."""

    def test_error_message_generated(self):
        """Test that error message is auto-generated."""
        error = UngroundedClaimError(
            claim_text="This is a long claim that should be truncated in the message",
            section="Test Section",
        )

        assert "no evidence" in error.message.lower()
        assert error.error_type == "ungrounded_claim"


class TestInvalidEvidenceRefError:
    """Tests for InvalidEvidenceRefError model."""

    def test_error_message_generated(self):
        """Test that error message is auto-generated."""
        error = InvalidEvidenceRefError(
            evidence_id="invalid_123",
            claim_text="Test claim",
            section="Test Section",
        )

        assert "invalid_123" in error.message
        assert "not found" in error.message.lower()
        assert error.error_type == "invalid_evidence_ref"


class TestValidateGroundingFunction:
    """Tests for validate_grounding convenience function."""

    def test_convenience_function(self, sample_evidence_pack):
        """Test the convenience function works correctly."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Test claim",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = validate_grounding(memo, sample_evidence_pack)

        assert isinstance(result, GroundingResult)
