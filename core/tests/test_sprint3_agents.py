"""
Sprint 3: Agent Tests

Tests for IntakeAgent, NarrativeAgent, and PolicyDraftAgent.
Tests schema validation, extraction, and safety invariants.

Updated for Gemini 3 SDK integration with context caching.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, '/Users/rk/Desktop/Governance-OS')


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_gemini_client():
    """Create a mocked Gemini client for testing agents."""
    with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
        with patch('google.genai.Client') as mock_genai:
            mock_instance = Mock()
            mock_genai.return_value = mock_instance

            # Mock cache operations
            mock_cache = Mock()
            mock_cache.name = "caches/test123"
            mock_instance.caches.create.return_value = mock_cache
            mock_instance.caches.get.return_value = mock_cache

            # Default response
            mock_response = Mock()
            mock_response.text = '[]'
            mock_instance.models.generate_content.return_value = mock_response

            # Reset cache manager singleton
            import coprocessor.cache.manager as manager_module
            manager_module._cache_manager = None

            yield mock_instance


# ============================================================================
# IntakeAgent Tests
# ============================================================================

class TestIntakeAgentInit:
    """Test IntakeAgent initialization."""

    def test_init_default(self, mock_gemini_client):
        """Test default initialization with Gemini 3."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        assert agent._client.model == "gemini-3-flash-preview"
        assert agent._use_cache is True

    def test_init_custom_model(self, mock_gemini_client):
        """Test initialization with custom model."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent(model="gemini-3-pro-preview")
        assert agent._client.model == "gemini-3-pro-preview"

    def test_init_cache_disabled(self, mock_gemini_client):
        """Test initialization with caching disabled."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent(use_cache=False)
        assert agent._use_cache is False
        assert agent._cache_manager is None

    def test_pack_prompt_treasury(self, mock_gemini_client):
        """Test getting treasury pack prompt."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        prompt = agent._get_pack_prompt("treasury")
        assert isinstance(prompt, str)

    def test_pack_prompt_wealth(self, mock_gemini_client):
        """Test getting wealth pack prompt."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        prompt = agent._get_pack_prompt("wealth")
        assert isinstance(prompt, str)

    def test_pack_prompt_invalid(self, mock_gemini_client):
        """Test getting prompt for invalid pack."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        with pytest.raises(ValueError, match="Unknown pack"):
            agent._get_pack_prompt("invalid_pack")


class TestIntakeAgentParsing:
    """Test IntakeAgent response parsing."""

    def test_parse_json_array(self, mock_gemini_client):
        """Test parsing a JSON array response."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        response = '[{"signal_type": "test", "confidence": 0.9}]'
        result = agent._parse_json_response(response)
        assert len(result) == 1
        assert result[0]["signal_type"] == "test"

    def test_parse_json_with_markdown(self, mock_gemini_client):
        """Test parsing JSON wrapped in markdown code blocks."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        response = '''Here are the signals:
```json
[{"signal_type": "position_limit_breach", "confidence": 0.85}]
```
'''
        result = agent._parse_json_response(response)
        assert len(result) == 1
        assert result[0]["signal_type"] == "position_limit_breach"

    def test_parse_json_object_with_candidates(self, mock_gemini_client):
        """Test parsing JSON object with candidates key."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        response = '{"candidates": [{"signal_type": "test", "confidence": 0.8}]}'
        result = agent._parse_json_response(response)
        assert len(result) == 1

    def test_parse_single_object(self, mock_gemini_client):
        """Test parsing a single JSON object."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        response = '{"signal_type": "test", "confidence": 0.8}'
        result = agent._parse_json_response(response)
        assert len(result) == 1
        assert result[0]["signal_type"] == "test"

    def test_parse_invalid_json(self, mock_gemini_client):
        """Test parsing invalid JSON."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        with pytest.raises(ValueError, match="Failed to parse"):
            agent._parse_json_response("not valid json {}")


class TestIntakeAgentBuildResult:
    """Test IntakeAgent result building and validation."""

    def test_build_valid_result(self, mock_gemini_client):
        """Test building a valid extraction result."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        candidates_data = [
            {
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "$120M", "limit": "$100M"},
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

    def test_build_result_filters_invalid_signal_type(self, mock_gemini_client):
        """Test that invalid signal types are filtered out."""
        from coprocessor.agents.intake_agent import IntakeAgent
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

    def test_build_result_filters_missing_source_spans(self, mock_gemini_client):
        """Test that candidates without source spans are filtered."""
        from coprocessor.agents.intake_agent import IntakeAgent
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

    def test_build_result_clamps_confidence(self, mock_gemini_client):
        """Test that confidence is clamped to valid range."""
        from coprocessor.agents.intake_agent import IntakeAgent
        agent = IntakeAgent()
        candidates_data = [
            {
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "$120M", "limit": "$100M"},
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

    def test_validate_extraction_valid(self, mock_gemini_client):
        """Test validation of valid extraction result."""
        from coprocessor.agents.intake_agent import IntakeAgent
        from coprocessor.schemas.extraction import (
            ExtractionResult, CandidateSignal, SourceSpan
        )

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

    def test_validate_extraction_invalid_signal_type(self, mock_gemini_client):
        """Test validation catches invalid signal type."""
        from coprocessor.agents.intake_agent import IntakeAgent
        from coprocessor.schemas.extraction import (
            ExtractionResult, CandidateSignal, SourceSpan
        )

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


class TestIntakeAgentSafetyInvariants:
    """Test IntakeAgent safety invariants."""

    def test_only_pack_vocabulary_signal_types(self, mock_gemini_client):
        """SAFETY: Agent must only output signal types from pack vocabulary."""
        from coprocessor.schemas.extraction import validate_signal_type_for_pack

        # Treasury signal types should be valid for treasury
        for signal_type in ["position_limit_breach", "counterparty_credit_downgrade"]:
            assert validate_signal_type_for_pack(signal_type, "treasury") is True

        # Wealth signal types should NOT be valid for treasury
        for signal_type in ["risk_tolerance_change", "suitability_drift"]:
            assert validate_signal_type_for_pack(signal_type, "treasury") is False

    def test_source_spans_required(self, mock_gemini_client):
        """SAFETY: Every extraction must have source spans."""
        from coprocessor.schemas.extraction import CandidateSignal

        # CandidateSignal requires at least one source span
        with pytest.raises(Exception):
            CandidateSignal(
                signal_type="test",
                payload={},
                confidence=0.9,
                source_spans=[],  # Empty source spans should fail
            )

    def test_confidence_bounded(self, mock_gemini_client):
        """SAFETY: Confidence scores must be in [0.0, 1.0]."""
        from coprocessor.schemas.extraction import CandidateSignal, SourceSpan

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


# ============================================================================
# NarrativeAgent Tests
# ============================================================================

class TestNarrativeAgentInit:
    """Test NarrativeAgent initialization."""

    def test_init_default(self, mock_gemini_client):
        """Test default initialization with Gemini 3."""
        from coprocessor.agents.narrative_agent import NarrativeAgent
        agent = NarrativeAgent()
        assert agent._client.model == "gemini-3-flash-preview"
        assert agent._use_cache is True

    def test_init_cache_disabled(self, mock_gemini_client):
        """Test initialization with caching disabled."""
        from coprocessor.agents.narrative_agent import NarrativeAgent
        agent = NarrativeAgent(use_cache=False)
        assert agent._use_cache is False

    def test_get_available_templates_treasury(self, mock_gemini_client):
        """Test getting templates for treasury pack."""
        from coprocessor.agents.narrative_agent import NarrativeAgent
        from coprocessor.schemas.narrative import MemoTemplate

        agent = NarrativeAgent()
        templates = agent.get_available_templates("treasury")

        assert MemoTemplate.TREASURY_LIQUIDITY in templates
        assert MemoTemplate.TREASURY_POSITION in templates
        assert MemoTemplate.DECISION_BRIEF in templates

    def test_get_available_templates_wealth(self, mock_gemini_client):
        """Test getting templates for wealth pack."""
        from coprocessor.agents.narrative_agent import NarrativeAgent
        from coprocessor.schemas.narrative import MemoTemplate

        agent = NarrativeAgent()
        templates = agent.get_available_templates("wealth")

        assert MemoTemplate.WEALTH_SUITABILITY in templates
        assert MemoTemplate.WEALTH_CLIENT in templates
        assert MemoTemplate.DECISION_BRIEF in templates


class TestNarrativeAgentValidation:
    """Test NarrativeAgent validation methods."""

    def test_validate_grounding_valid(self, mock_gemini_client):
        """Test validation of properly grounded memo."""
        from coprocessor.agents.narrative_agent import NarrativeAgent
        from coprocessor.schemas.narrative import (
            NarrativeMemo, MemoSection, NarrativeClaim, EvidenceReference
        )

        agent = NarrativeAgent()

        memo = NarrativeMemo(
            decision_id="test-123",
            title="Test Memo",
            sections=[
                MemoSection(
                    heading="Summary",
                    claims=[
                        NarrativeClaim(
                            text="The position exceeded the limit",
                            evidence_refs=[
                                EvidenceReference(
                                    evidence_id="sig_abc123",
                                    evidence_type="signal",
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        evidence_pack = {
            "evidence_items": [
                {"evidence_id": "sig_abc123", "type": "signal"}
            ]
        }

        errors = agent.validate_grounding(memo, evidence_pack)
        assert len(errors) == 0

    def test_validate_grounding_ungrounded_claim(self, mock_gemini_client):
        """Test validation catches claims with invalid evidence refs."""
        from coprocessor.agents.narrative_agent import NarrativeAgent
        from coprocessor.schemas.narrative import (
            NarrativeMemo, MemoSection, NarrativeClaim, EvidenceReference
        )

        agent = NarrativeAgent()

        # Note: NarrativeClaim schema enforces at least 1 evidence_ref (safety invariant)
        # So we test with a reference to non-existent evidence instead
        memo = NarrativeMemo(
            decision_id="test-123",
            title="Test Memo",
            sections=[
                MemoSection(
                    heading="Summary",
                    claims=[
                        NarrativeClaim(
                            text="This claim refs non-existent evidence",
                            evidence_refs=[
                                EvidenceReference(
                                    evidence_id="sig_does_not_exist",
                                    evidence_type="signal",
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        # Empty evidence pack means ref is invalid
        evidence_pack = {"evidence_items": []}

        errors = agent.validate_grounding(memo, evidence_pack)
        assert len(errors) > 0
        assert "not found" in errors[0].lower()

    def test_validate_grounding_invalid_reference(self, mock_gemini_client):
        """Test validation catches invalid evidence references."""
        from coprocessor.agents.narrative_agent import NarrativeAgent
        from coprocessor.schemas.narrative import (
            NarrativeMemo, MemoSection, NarrativeClaim, EvidenceReference
        )

        agent = NarrativeAgent()

        memo = NarrativeMemo(
            decision_id="test-123",
            title="Test Memo",
            sections=[
                MemoSection(
                    heading="Summary",
                    claims=[
                        NarrativeClaim(
                            text="Claim with fake reference",
                            evidence_refs=[
                                EvidenceReference(
                                    evidence_id="sig_nonexistent",
                                    evidence_type="signal",
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        # Evidence pack doesn't contain the referenced ID
        evidence_pack = {
            "evidence_items": [
                {"evidence_id": "sig_other", "type": "signal"}
            ]
        }

        errors = agent.validate_grounding(memo, evidence_pack)
        assert len(errors) > 0
        assert "not found" in errors[0].lower()


# ============================================================================
# PolicyDraftAgent Tests
# ============================================================================

class TestPolicyDraftAgentInit:
    """Test PolicyDraftAgent initialization."""

    def test_init_default(self, mock_gemini_client):
        """Test default initialization with Gemini 3."""
        from coprocessor.agents.policy_draft_agent import PolicyDraftAgent
        agent = PolicyDraftAgent()
        assert agent._client.model == "gemini-3-flash-preview"
        assert agent._use_cache is True

    def test_init_cache_disabled(self, mock_gemini_client):
        """Test initialization with caching disabled."""
        from coprocessor.agents.policy_draft_agent import PolicyDraftAgent
        agent = PolicyDraftAgent(use_cache=False)
        assert agent._use_cache is False


class TestPolicyDraftAgentSchemas:
    """Test PolicyDraftAgent schemas."""

    def test_policy_draft_schema(self, mock_gemini_client):
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

    def test_validate_rule_definition(self, mock_gemini_client):
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


class TestPolicyDraftAgentValidation:
    """Test PolicyDraftAgent validation methods."""

    def test_validate_draft_valid(self, mock_gemini_client):
        """Test validation of valid policy draft."""
        from coprocessor.agents.policy_draft_agent import PolicyDraftAgent
        from coprocessor.schemas.policy_draft import PolicyDraft, TestScenario

        agent = PolicyDraftAgent()

        draft = PolicyDraft(
            name="Test Policy",
            description="Test description",
            rule_definition={
                "type": "threshold",
                "signal_type": "position_limit_breach",
                "field": "payload.position",
                "operator": "gt",
                "threshold": 100,
            },
            signal_types_referenced=["position_limit_breach"],
            change_reason="Test",
            pack="treasury",
            test_scenarios=[
                TestScenario(
                    description="Test 1",
                    input_signals=[{"type": "test"}],
                    expected_result="pass",
                ),
                TestScenario(
                    description="Test 2",
                    input_signals=[{"type": "test"}],
                    expected_result="fail",
                ),
            ],
        )

        errors = agent.validate_draft(draft)
        assert len(errors) == 0

    def test_validate_draft_missing_test_scenarios(self, mock_gemini_client):
        """Test validation catches missing test scenarios."""
        from coprocessor.agents.policy_draft_agent import PolicyDraftAgent
        from coprocessor.schemas.policy_draft import PolicyDraft

        agent = PolicyDraftAgent()

        draft = PolicyDraft(
            name="Test Policy",
            description="Test description",
            rule_definition={"type": "threshold"},
            signal_types_referenced=["position_limit_breach"],
            change_reason="Test",
            pack="treasury",
            test_scenarios=[],  # No scenarios
        )

        errors = agent.validate_draft(draft)
        assert any("2 test scenarios" in e for e in errors)


# ============================================================================
# Cache Integration Tests
# ============================================================================

class TestAgentCacheIntegration:
    """Test agent integration with Gemini 3 context caching."""

    def test_intake_agent_builds_cache_on_first_call(self, mock_gemini_client):
        """Test that IntakeAgent builds cache on first extraction."""
        mock_gemini_client.models.generate_content.return_value.text = '[]'

        from coprocessor.agents.intake_agent import IntakeAgent
        # Disable thinking mode - this test is for cache behavior
        agent = IntakeAgent(use_cache=True, use_thinking=False)

        result = agent.extract_signals_sync(
            content="Test document",
            pack="treasury",
            document_source="test",
        )

        # Cache should have been created
        assert mock_gemini_client.caches.create.called

    def test_narrative_agent_with_cache(self, mock_gemini_client):
        """Test NarrativeAgent uses cache."""
        mock_gemini_client.models.generate_content.return_value.text = '''
        {
            "title": "Test Memo",
            "sections": [
                {
                    "heading": "Summary",
                    "claims": [
                        {"text": "Test claim", "evidence_refs": ["sig_123"]}
                    ]
                }
            ],
            "uncertainties": [],
            "assumptions": []
        }
        '''

        from coprocessor.agents.narrative_agent import NarrativeAgent
        agent = NarrativeAgent(use_cache=True)

        evidence_pack = {
            "evidence_pack_id": "pack_123",
            "evidence_items": [
                {"evidence_id": "sig_123", "type": "signal", "data": {}}
            ]
        }

        memo = agent.draft_memo_sync(
            decision_id="dec_123",
            evidence_pack=evidence_pack,
            pack="treasury",
        )

        assert memo.title == "Test Memo"
        assert mock_gemini_client.models.generate_content.called

    def test_policy_draft_agent_with_cache(self, mock_gemini_client):
        """Test PolicyDraftAgent uses cache."""
        mock_gemini_client.models.generate_content.return_value.text = '''
        {
            "name": "Test Policy",
            "description": "Test description",
            "rule_definition": {"type": "threshold", "signal_type": "position_limit_breach"},
            "signal_types_referenced": ["position_limit_breach"],
            "change_reason": "New policy",
            "draft_notes": "Generated draft",
            "test_scenarios": [
                {"description": "Test 1", "input_signals": [], "expected_result": "pass"},
                {"description": "Test 2", "input_signals": [], "expected_result": "fail"}
            ]
        }
        '''

        from coprocessor.agents.policy_draft_agent import PolicyDraftAgent
        agent = PolicyDraftAgent(use_cache=True)

        result = agent.generate_draft_sync(
            description="Create a policy for position limits",
            pack="treasury",
        )

        assert result.draft.name == "Test Policy"
        assert mock_gemini_client.models.generate_content.called
