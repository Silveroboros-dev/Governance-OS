"""
Sprint 3: Schema Tests

Tests for extraction and policy draft schemas.
Validates data models and constraints.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

# Import schemas
import sys
sys.path.insert(0, '/Users/rk/Desktop/Governance-OS')

from coprocessor.schemas.extraction import (
    SourceSpan,
    CandidateSignal,
    ExtractionResult,
    ExtractionValidationResult,
    validate_signal_type_for_pack,
    get_valid_signal_types,
    TREASURY_SIGNAL_TYPES,
    WEALTH_SIGNAL_TYPES,
)


class TestSourceSpan:
    """Test SourceSpan schema."""

    def test_valid_source_span(self):
        """Test creating a valid source span."""
        span = SourceSpan(
            start_char=10,
            end_char=50,
            text="The current position is $120M",
        )
        assert span.start_char == 10
        assert span.end_char == 50
        assert span.text == "The current position is $120M"
        assert span.page is None

    def test_source_span_with_page(self):
        """Test source span with page number."""
        span = SourceSpan(
            start_char=100,
            end_char=200,
            text="Risk assessment indicates...",
            page=3,
        )
        assert span.page == 3

    def test_empty_text_fails(self):
        """Test that empty text is rejected."""
        with pytest.raises(ValidationError):
            SourceSpan(
                start_char=10,
                end_char=50,
                text="",
            )

    def test_whitespace_only_text_fails(self):
        """Test that whitespace-only text is rejected."""
        with pytest.raises(ValidationError):
            SourceSpan(
                start_char=10,
                end_char=50,
                text="   ",
            )

    def test_negative_start_char_fails(self):
        """Test that negative start_char is rejected."""
        with pytest.raises(ValidationError):
            SourceSpan(
                start_char=-1,
                end_char=50,
                text="test",
            )

    def test_end_before_start_fails(self):
        """Test that end_char < start_char is rejected."""
        with pytest.raises(ValidationError):
            SourceSpan(
                start_char=50,
                end_char=10,
                text="test",
            )

    def test_zero_page_fails(self):
        """Test that page 0 is rejected (pages are 1-indexed)."""
        with pytest.raises(ValidationError):
            SourceSpan(
                start_char=10,
                end_char=50,
                text="test",
                page=0,
            )


class TestCandidateSignal:
    """Test CandidateSignal schema."""

    def test_valid_candidate_signal(self):
        """Test creating a valid candidate signal."""
        signal = CandidateSignal(
            signal_type="position_limit_breach",
            payload={"asset": "BTC", "position": 120, "limit": 100},
            confidence=0.85,
            source_spans=[
                SourceSpan(start_char=10, end_char=50, text="BTC position is $120M")
            ],
        )
        assert signal.signal_type == "position_limit_breach"
        assert signal.confidence == 0.85
        assert len(signal.source_spans) == 1

    def test_requires_verification_low_confidence(self):
        """Test requires_verification property."""
        signal = CandidateSignal(
            signal_type="test",
            payload={},
            confidence=0.5,
            source_spans=[SourceSpan(start_char=0, end_char=10, text="test text")],
        )
        assert signal.requires_verification is True

    def test_requires_verification_high_confidence(self):
        """Test requires_verification with high confidence."""
        signal = CandidateSignal(
            signal_type="test",
            payload={},
            confidence=0.9,
            source_spans=[SourceSpan(start_char=0, end_char=10, text="test text")],
        )
        assert signal.requires_verification is False

    def test_is_high_confidence(self):
        """Test is_high_confidence property."""
        high = CandidateSignal(
            signal_type="test",
            payload={},
            confidence=0.95,
            source_spans=[SourceSpan(start_char=0, end_char=10, text="test text")],
        )
        assert high.is_high_confidence is True

        medium = CandidateSignal(
            signal_type="test",
            payload={},
            confidence=0.85,
            source_spans=[SourceSpan(start_char=0, end_char=10, text="test text")],
        )
        assert medium.is_high_confidence is False

    def test_empty_signal_type_fails(self):
        """Test that empty signal_type is rejected."""
        with pytest.raises(ValidationError):
            CandidateSignal(
                signal_type="",
                payload={},
                confidence=0.8,
                source_spans=[SourceSpan(start_char=0, end_char=10, text="test")],
            )

    def test_confidence_out_of_range_fails(self):
        """Test that confidence outside 0-1 is rejected."""
        with pytest.raises(ValidationError):
            CandidateSignal(
                signal_type="test",
                payload={},
                confidence=1.5,
                source_spans=[SourceSpan(start_char=0, end_char=10, text="test")],
            )

        with pytest.raises(ValidationError):
            CandidateSignal(
                signal_type="test",
                payload={},
                confidence=-0.1,
                source_spans=[SourceSpan(start_char=0, end_char=10, text="test")],
            )

    def test_no_source_spans_fails(self):
        """Test that at least one source span is required."""
        with pytest.raises(ValidationError):
            CandidateSignal(
                signal_type="test",
                payload={},
                confidence=0.8,
                source_spans=[],
            )

    def test_multiple_source_spans(self):
        """Test signal with multiple source spans."""
        signal = CandidateSignal(
            signal_type="test",
            payload={"field1": "value1", "field2": "value2"},
            confidence=0.9,
            source_spans=[
                SourceSpan(start_char=10, end_char=30, text="field1 value"),
                SourceSpan(start_char=50, end_char=70, text="field2 value"),
            ],
        )
        assert len(signal.source_spans) == 2


class TestExtractionResult:
    """Test ExtractionResult schema."""

    def test_valid_extraction_result(self):
        """Test creating a valid extraction result."""
        result = ExtractionResult(
            document_source="email/inbox/123",
            document_metadata={"sender": "cfo@company.com"},
            pack="treasury",
            candidates=[
                CandidateSignal(
                    signal_type="position_limit_breach",
                    payload={"asset": "BTC"},
                    confidence=0.9,
                    source_spans=[SourceSpan(start_char=0, end_char=20, text="BTC breach")],
                ),
            ],
        )
        assert result.total_candidates == 1
        assert result.high_confidence_count == 1
        assert result.requires_verification_count == 0

    def test_empty_extraction_result(self):
        """Test extraction result with no candidates."""
        result = ExtractionResult(
            document_source="email/inbox/456",
            pack="treasury",
        )
        assert result.total_candidates == 0
        assert result.high_confidence_count == 0
        assert result.requires_verification_count == 0

    def test_get_candidates_by_type(self):
        """Test filtering candidates by type."""
        result = ExtractionResult(
            document_source="test",
            pack="treasury",
            candidates=[
                CandidateSignal(
                    signal_type="position_limit_breach",
                    payload={},
                    confidence=0.9,
                    source_spans=[SourceSpan(start_char=0, end_char=10, text="test")],
                ),
                CandidateSignal(
                    signal_type="position_limit_breach",
                    payload={},
                    confidence=0.8,
                    source_spans=[SourceSpan(start_char=20, end_char=30, text="test")],
                ),
                CandidateSignal(
                    signal_type="credit_rating_change",
                    payload={},
                    confidence=0.75,
                    source_spans=[SourceSpan(start_char=40, end_char=50, text="test")],
                ),
            ],
        )

        breaches = result.get_candidates_by_type("position_limit_breach")
        assert len(breaches) == 2

        credit = result.get_candidates_by_type("credit_rating_change")
        assert len(credit) == 1

        unknown = result.get_candidates_by_type("unknown_type")
        assert len(unknown) == 0


class TestSignalTypeValidation:
    """Test signal type validation functions."""

    def test_valid_treasury_signal_types(self):
        """Test valid treasury signal types."""
        for signal_type in TREASURY_SIGNAL_TYPES:
            assert validate_signal_type_for_pack(signal_type, "treasury") is True

    def test_valid_wealth_signal_types(self):
        """Test valid wealth signal types."""
        for signal_type in WEALTH_SIGNAL_TYPES:
            assert validate_signal_type_for_pack(signal_type, "wealth") is True

    def test_invalid_signal_type(self):
        """Test invalid signal type."""
        assert validate_signal_type_for_pack("unknown_type", "treasury") is False
        assert validate_signal_type_for_pack("unknown_type", "wealth") is False

    def test_wrong_pack_signal_type(self):
        """Test signal type from wrong pack."""
        # Treasury type in wealth pack
        assert validate_signal_type_for_pack("position_limit_breach", "wealth") is False
        # Wealth type in treasury pack
        assert validate_signal_type_for_pack("risk_tolerance_change", "treasury") is False

    def test_invalid_pack(self):
        """Test validation with invalid pack."""
        assert validate_signal_type_for_pack("position_limit_breach", "unknown_pack") is False

    def test_get_valid_signal_types(self):
        """Test getting valid signal types for a pack."""
        treasury_types = get_valid_signal_types("treasury")
        assert treasury_types == TREASURY_SIGNAL_TYPES
        assert "position_limit_breach" in treasury_types

        wealth_types = get_valid_signal_types("wealth")
        assert wealth_types == WEALTH_SIGNAL_TYPES
        assert "risk_tolerance_change" in wealth_types

        unknown_types = get_valid_signal_types("unknown")
        assert unknown_types == []
