"""
Tests for Hallucination Detector - Detects forbidden patterns in narratives.
"""

import pytest

from evals.validators.hallucination import (
    HallucinationDetector,
    HallucinationResult,
    HallucinationError,
    detect_hallucinations,
)
from coprocessor.schemas.narrative import (
    NarrativeMemo,
    NarrativeClaim,
    EvidenceReference,
    MemoSection,
)


class TestHallucinationDetector:
    """Tests for HallucinationDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a hallucination detector."""
        return HallucinationDetector()

    @pytest.fixture
    def detector_no_grounding_check(self):
        """Create a detector that doesn't check grounding."""
        return HallucinationDetector(check_grounding=False)

    @pytest.fixture
    def clean_memo(self):
        """Create a memo without any forbidden patterns."""
        sections = [
            MemoSection(
                heading="Situation",
                claims=[
                    NarrativeClaim(
                        text="The BTC position reached $150M, exceeding the $100M limit",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                    NarrativeClaim(
                        text="The exception was classified as high severity by the kernel",
                        evidence_refs=[EvidenceReference(evidence_id="eval_001")],
                    ),
                ],
            ),
            MemoSection(
                heading="Decision",
                claims=[
                    NarrativeClaim(
                        text="The decision-maker chose to reduce the position",
                        evidence_refs=[EvidenceReference(evidence_id="opt_001")],
                    ),
                ],
            ),
        ]
        return NarrativeMemo(
            decision_id="dec_001",
            title="Position Limit Breach Resolution",
            sections=sections,
        )

    def test_detect_clean_memo(self, detector, clean_memo):
        """Test detection on a clean memo."""
        result = detector.detect(clean_memo)

        assert result.passed is True
        assert result.total_claims == 3
        assert result.clean_claims == 3
        assert len(result.errors) == 0

    def test_detect_recommendation_should(self, detector):
        """Test detection of 'should' recommendation."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="The team should consider reducing exposure",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert len(result.errors) >= 1
        assert any(e.error_type == "recommendation" for e in result.errors)
        assert any("should" in e.pattern_matched.lower() for e in result.errors)

    def test_detect_recommendation_recommend(self, detector):
        """Test detection of 'recommend' language."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="We recommend immediate action on this exception",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert result.errors[0].error_type == "recommendation"

    def test_detect_recommendation_best_option(self, detector):
        """Test detection of 'best option' language."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="The best option here is to reduce position",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert result.errors[0].error_type == "recommendation"

    def test_detect_opinion_i_think(self, detector):
        """Test detection of 'I think' opinion."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="I think this situation requires immediate attention",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert result.errors[0].error_type == "opinion"

    def test_detect_opinion_appears_to_be(self, detector):
        """Test detection of 'appears to be' opinion."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="This appears to be a significant risk",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert result.errors[0].error_type == "opinion"

    def test_detect_opinion_probably(self, detector):
        """Test detection of 'probably' opinion."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="The position will probably need to be reduced",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert result.errors[0].error_type == "opinion"

    def test_detect_severity_judgment(self, detector):
        """Test detection of severity judgment (kernel's job)."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="This is critical and requires immediate attention",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert result.errors[0].error_type == "severity_judgment"

    def test_detect_policy_evaluation(self, detector):
        """Test detection of policy evaluation (kernel's job)."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="The policy threshold is too strict for this situation",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert result.errors[0].error_type == "policy_evaluation"

    def test_detect_multiple_issues(self, detector):
        """Test detection of multiple issues in one memo."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="I think the team should act immediately",  # opinion + recommendation
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.passed is False
        assert len(result.errors) >= 2

    def test_hallucination_rate_calculation(self, detector):
        """Test hallucination rate calculation."""
        sections = [
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="Clean factual statement",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                    NarrativeClaim(
                        text="The team should consider this",
                        evidence_refs=[EvidenceReference(evidence_id="sig_002")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detector.detect(memo)

        assert result.hallucination_rate == 50.0  # 1 of 2 claims has issues

    def test_is_clean_method(self, detector):
        """Test quick is_clean check."""
        assert detector.is_clean("The position exceeded the limit") is True
        assert detector.is_clean("The team should reduce position") is False
        assert detector.is_clean("I think this is important") is False
        assert detector.is_clean("This is critical") is False

    def test_detect_in_text_method(self, detector):
        """Test detection in raw text."""
        errors = detector.detect_in_text("The team should consider reducing exposure")

        assert len(errors) > 0
        assert errors[0].error_type == "recommendation"

    def test_custom_forbidden_patterns(self):
        """Test custom forbidden patterns."""
        detector = HallucinationDetector(
            custom_forbidden_patterns=[r"\bfoo\b", r"\bbar\b"]
        )

        assert detector.is_clean("This contains foo") is False
        assert detector.is_clean("This contains bar") is False
        assert detector.is_clean("This contains baz") is True

    def test_case_insensitive_detection(self, detector):
        """Test that detection is case insensitive."""
        assert detector.is_clean("SHOULD do this") is False
        assert detector.is_clean("Should do this") is False
        assert detector.is_clean("should do this") is False

    def test_empty_memo(self, detector):
        """Test detection on empty memo."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Empty",
            sections=[],
        )

        result = detector.detect(memo)

        assert result.passed is True
        assert result.hallucination_rate == 0.0


class TestHallucinationResult:
    """Tests for HallucinationResult model."""

    def test_hallucination_rate_zero_claims(self):
        """Test hallucination rate with zero claims."""
        result = HallucinationResult(
            passed=True,
            total_claims=0,
            clean_claims=0,
        )
        assert result.hallucination_rate == 0.0


class TestHallucinationError:
    """Tests for HallucinationError model."""

    def test_error_creation(self):
        """Test error creation."""
        error = HallucinationError(
            error_type="recommendation",
            claim_text="The team should act",
            section="Analysis",
            pattern_matched="should",
            message="Forbidden pattern detected",
        )

        assert error.error_type == "recommendation"
        assert error.pattern_matched == "should"


class TestDetectHallucinationsFunction:
    """Tests for detect_hallucinations convenience function."""

    def test_convenience_function(self):
        """Test the convenience function works correctly."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Clean statement",
                        evidence_refs=[EvidenceReference(evidence_id="sig_001")],
                    ),
                ],
            ),
        ]
        memo = NarrativeMemo(decision_id="dec_001", title="Test", sections=sections)

        result = detect_hallucinations(memo)

        assert isinstance(result, HallucinationResult)
        assert result.passed is True
