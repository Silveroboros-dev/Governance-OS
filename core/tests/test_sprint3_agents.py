"""
Sprint 3: Agent Tests

Tests for IntakeAgent and PolicyDraftAgent.
Tests schema validation, extraction, and safety invariants.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, '/Users/rk/Desktop/Governance-OS')

from coprocessor.agents.intake_agent import IntakeAgent
from coprocessor.schemas.extraction import (
    CandidateSignal,
    SourceSpan,
    ExtractionResult,
    validate_signal_type_for_pack,
)


class TestIntakeAgentInit:
    """Test IntakeAgent initialization."""

    def test_init_default(self):
        """Test default initialization."""
        agent = IntakeAgent()
        assert agent.model == "claude-sonnet-4-20250514"
        assert agent._client is None  # Lazy initialization

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        agent = IntakeAgent(model="claude-3-haiku-20240307")
        assert agent.model == "claude-3-haiku-20240307"

    def test_pack_prompt_treasury(self):
        """Test getting treasury pack prompt."""
        agent = IntakeAgent()
        # Should not raise
        prompt = agent._get_pack_prompt("treasury")
        assert isinstance(prompt, str)

    def test_pack_prompt_wealth(self):
        """Test getting wealth pack prompt."""
        agent = IntakeAgent()
        prompt = agent._get_pack_prompt("wealth")
        assert isinstance(prompt, str)

    def test_pack_prompt_invalid(self):
        """Test getting prompt for invalid pack."""
        agent = IntakeAgent()
        with pytest.raises(ValueError, match="Unknown pack"):
            agent._get_pack_prompt("invalid_pack")


class TestIntakeAgentParsing:
    """Test IntakeAgent response parsing."""

    def test_parse_json_array(self):
        """Test parsing a JSON array response."""
        agent = IntakeAgent()
        response = '[{"signal_type": "test", "confidence": 0.9}]'
        result = agent._parse_json_response(response)
        assert len(result) == 1
        assert result[0]["signal_type"] == "test"

    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        agent = IntakeAgent()
        response = '''Here are the signals:
```json
[{"signal_type": "position_limit_breach", "confidence": 0.85}]
```
'''
        result = agent._parse_json_response(response)
        assert len(result) == 1
        assert result[0]["signal_type"] == "position_limit_breach"

    def test_parse_json_object_with_candidates(self):
        """Test parsing JSON object with candidates key."""
        agent = IntakeAgent()
        response = '{"candidates": [{"signal_type": "test", "confidence": 0.8}]}'
        result = agent._parse_json_response(response)
        assert len(result) == 1

    def test_parse_single_object(self):
        """Test parsing a single JSON object."""
        agent = IntakeAgent()
        response = '{"signal_type": "test", "confidence": 0.8}'
        result = agent._parse_json_response(response)
        assert len(result) == 1
        assert result[0]["signal_type"] == "test"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        agent = IntakeAgent()
        with pytest.raises(ValueError, match="Failed to parse"):
            agent._parse_json_response("not valid json {}")


class TestIntakeAgentBuildResult:
    """Test IntakeAgent result building and validation."""

    def test_build_valid_result(self):
        """Test building a valid extraction result."""
        agent = IntakeAgent()
        candidates_data = [
            {
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "position": 120},
                "confidence": 0.85,
                "source_spans": [
                    {"start_char": 10, "end_char": 50, "text": "BTC position $120M"}
                ],
                "extraction_notes": "Found in paragraph 1",
            }
        ]

        result = agent._build_extraction_result(
            candidates_data=candidates_data,
            pack="treasury",
            document_source="email/inbox/123",
            document_metadata={"sender": "cfo@test.com"},
            content="The BTC position $120M exceeds the limit.",
        )

        assert result.total_candidates == 1
        assert result.candidates[0].signal_type == "position_limit_breach"
        assert result.candidates[0].confidence == 0.85
        assert len(result.candidates[0].source_spans) == 1

    def test_build_result_filters_invalid_signal_type(self):
        """Test that invalid signal types are filtered out."""
        agent = IntakeAgent()
        candidates_data = [
            {
                "signal_type": "invalid_type",  # Not in treasury vocabulary
                "payload": {},
                "confidence": 0.9,
                "source_spans": [{"start_char": 0, "end_char": 10, "text": "test"}],
            },
            {
                "signal_type": "position_limit_breach",  # Valid
                "payload": {},
                "confidence": 0.8,
                "source_spans": [{"start_char": 20, "end_char": 30, "text": "test"}],
            },
        ]

        result = agent._build_extraction_result(
            candidates_data=candidates_data,
            pack="treasury",
            document_source="test",
            document_metadata={},
            content="test content here and there",
        )

        # Only valid signal should remain
        assert result.total_candidates == 1
        assert result.candidates[0].signal_type == "position_limit_breach"
        assert "invalid signal_type" in result.extraction_notes.lower()

    def test_build_result_filters_missing_source_spans(self):
        """Test that candidates without source spans are filtered."""
        agent = IntakeAgent()
        candidates_data = [
            {
                "signal_type": "position_limit_breach",
                "payload": {},
                "confidence": 0.9,
                "source_spans": [],  # No source spans
            },
        ]

        result = agent._build_extraction_result(
            candidates_data=candidates_data,
            pack="treasury",
            document_source="test",
            document_metadata={},
            content="test content",
        )

        # Should be filtered out
        assert result.total_candidates == 0
        assert "no valid source spans" in result.extraction_notes.lower()

    def test_build_result_clamps_confidence(self):
        """Test that confidence is clamped to valid range."""
        agent = IntakeAgent()
        candidates_data = [
            {
                "signal_type": "position_limit_breach",
                "payload": {},
                "confidence": 1.5,  # Out of range
                "source_spans": [{"start_char": 0, "end_char": 10, "text": "test"}],
            },
        ]

        result = agent._build_extraction_result(
            candidates_data=candidates_data,
            pack="treasury",
            document_source="test",
            document_metadata={},
            content="test content",
        )

        # Confidence should be clamped to 1.0
        assert result.candidates[0].confidence == 1.0


class TestIntakeAgentValidation:
    """Test IntakeAgent validation methods."""

    def test_validate_extraction_valid(self):
        """Test validation of valid extraction result."""
        agent = IntakeAgent()
        content = "The BTC position is at $120M, which exceeds our limit."

        result = ExtractionResult(
            document_source="test",
            pack="treasury",
            candidates=[
                CandidateSignal(
                    signal_type="position_limit_breach",
                    payload={"asset": "BTC", "position": 120},
                    confidence=0.85,
                    source_spans=[
                        SourceSpan(
                            start_char=4,
                            end_char=25,
                            text="BTC position is at $120M",
                        )
                    ],
                )
            ],
        )

        errors = agent.validate_extraction(result, content)
        assert len(errors) == 0

    def test_validate_extraction_invalid_signal_type(self):
        """Test validation catches invalid signal type."""
        agent = IntakeAgent()
        content = "test content"

        # Create result with signal type not in pack vocabulary
        result = ExtractionResult(
            document_source="test",
            pack="treasury",
            candidates=[
                CandidateSignal(
                    signal_type="risk_tolerance_change",  # Wealth type, not treasury
                    payload={},
                    confidence=0.85,
                    source_spans=[
                        SourceSpan(start_char=0, end_char=5, text="test ")
                    ],
                )
            ],
        )

        errors = agent.validate_extraction(result, content)
        assert len(errors) > 0
        assert "invalid signal_type" in errors[0].lower()

    def test_validate_extraction_out_of_range_spans(self):
        """Test validation catches out-of-range character offsets."""
        agent = IntakeAgent()
        content = "short"  # Only 5 characters

        result = ExtractionResult(
            document_source="test",
            pack="treasury",
            candidates=[
                CandidateSignal(
                    signal_type="position_limit_breach",
                    payload={},
                    confidence=0.85,
                    source_spans=[
                        SourceSpan(
                            start_char=0,
                            end_char=100,  # Way beyond content length
                            text="this text doesn't match",
                        )
                    ],
                )
            ],
        )

        errors = agent.validate_extraction(result, content)
        assert len(errors) > 0
        assert "out of range" in errors[0].lower()


class TestIntakeAgentSafetyInvariants:
    """Test IntakeAgent safety invariants."""

    def test_only_pack_vocabulary_signal_types(self):
        """SAFETY: Agent must only output signal types from pack vocabulary."""
        agent = IntakeAgent()

        # Treasury signal types should be valid for treasury
        for signal_type in ["position_limit_breach", "counterparty_exposure_change"]:
            assert validate_signal_type_for_pack(signal_type, "treasury") is True

        # Wealth signal types should NOT be valid for treasury
        for signal_type in ["risk_tolerance_change", "beneficiary_update"]:
            assert validate_signal_type_for_pack(signal_type, "treasury") is False

    def test_source_spans_required(self):
        """SAFETY: Every extraction must have source spans."""
        # CandidateSignal requires at least one source span
        with pytest.raises(Exception):
            CandidateSignal(
                signal_type="test",
                payload={},
                confidence=0.9,
                source_spans=[],  # Empty source spans should fail
            )

    def test_confidence_bounded(self):
        """SAFETY: Confidence scores must be in [0.0, 1.0]."""
        # Confidence > 1.0 should fail
        with pytest.raises(Exception):
            CandidateSignal(
                signal_type="test",
                payload={},
                confidence=1.5,
                source_spans=[SourceSpan(start_char=0, end_char=10, text="test")],
            )

        # Confidence < 0.0 should fail
        with pytest.raises(Exception):
            CandidateSignal(
                signal_type="test",
                payload={},
                confidence=-0.1,
                source_spans=[SourceSpan(start_char=0, end_char=10, text="test")],
            )


class TestPolicyDraftAgentSchemas:
    """Test PolicyDraftAgent schemas."""

    def test_policy_draft_schema(self):
        """Test PolicyDraft schema validation."""
        from coprocessor.schemas.policy_draft import (
            PolicyDraft,
            TestScenario,
        )

        scenario = TestScenario(
            description="Position exceeds limit",
            input_signals=[{"type": "position_limit_breach", "payload": {"position": 120, "limit": 100}}],
            expected_result="exception_raised",
        )

        draft = PolicyDraft(
            name="Position Limit Policy",
            description="Monitors position limit breaches",
            rule_definition={
                "type": "threshold",
                "signal_type": "position_limit_breach",
                "field": "payload.position",
                "operator": "gt",
                "threshold": 100,
            },
            signal_types_referenced=["position_limit_breach"],
            change_reason="New policy for position monitoring",
            pack="treasury",
            test_scenarios=[scenario],
        )

        assert draft.name == "Position Limit Policy"
        assert draft.rule_definition["type"] == "threshold"
        assert len(draft.test_scenarios) == 1

    def test_policy_draft_empty_name_fails(self):
        """Test PolicyDraft with empty name fails."""
        from coprocessor.schemas.policy_draft import PolicyDraft

        with pytest.raises(Exception):
            PolicyDraft(
                name="",  # Empty name
                description="Test",
                rule_definition={"type": "threshold"},
                signal_types_referenced=["test"],
                change_reason="Test",
            )

    def test_policy_draft_empty_rule_definition_fails(self):
        """Test PolicyDraft with empty rule_definition fails."""
        from coprocessor.schemas.policy_draft import PolicyDraft

        with pytest.raises(Exception):
            PolicyDraft(
                name="Test Policy",
                description="Test",
                rule_definition={},  # Empty rule definition
                signal_types_referenced=["test"],
                change_reason="Test",
            )

    def test_policy_draft_missing_type_in_rule_fails(self):
        """Test PolicyDraft with missing type in rule_definition fails."""
        from coprocessor.schemas.policy_draft import PolicyDraft

        with pytest.raises(Exception):
            PolicyDraft(
                name="Test Policy",
                description="Test",
                rule_definition={"signal_type": "test"},  # Missing type
                signal_types_referenced=["test"],
                change_reason="Test",
            )

    def test_test_scenario_schema(self):
        """Test TestScenario schema."""
        from coprocessor.schemas.policy_draft import TestScenario

        scenario = TestScenario(
            description="Test scenario description",
            input_signals=[{"type": "test", "payload": {"value": 1}}],
            expected_result="pass",
        )

        assert scenario.description == "Test scenario description"
        assert len(scenario.input_signals) == 1

    def test_validate_rule_definition(self):
        """Test rule definition validation."""
        from coprocessor.schemas.policy_draft import validate_rule_definition

        # Valid threshold rule
        valid_rule = {
            "type": "threshold",
            "signal_type": "position_limit_breach",
            "field": "payload.position",
            "operator": "gt",
            "threshold": 100,
        }
        errors = validate_rule_definition(
            valid_rule,
            "treasury",
            ["position_limit_breach", "credit_rating_change"]
        )
        assert len(errors) == 0

        # Invalid rule - missing type
        invalid_rule = {
            "signal_type": "position_limit_breach",
        }
        errors = validate_rule_definition(
            invalid_rule,
            "treasury",
            ["position_limit_breach"]
        )
        assert len(errors) > 0

    def test_is_update_property(self):
        """Test is_update property."""
        from coprocessor.schemas.policy_draft import PolicyDraft

        new_draft = PolicyDraft(
            name="New Policy",
            description="Test",
            rule_definition={"type": "threshold"},
            signal_types_referenced=["test"],
            change_reason="New policy",
        )
        assert new_draft.is_update is False

        update_draft = PolicyDraft(
            name="Updated Policy",
            description="Test",
            rule_definition={"type": "threshold"},
            signal_types_referenced=["test"],
            change_reason="Update existing policy",
            policy_id="existing-policy-id",
        )
        assert update_draft.is_update is True
