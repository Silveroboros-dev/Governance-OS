"""
Tests for NarrativeAgent v1 - AI agent that drafts grounded memos.

Tests cover:
- Basic initialization and configuration
- Multi-template support (treasury/wealth-specific templates)
- Short/standard/detailed length variants
- Evidence grounding validation
- Uncertainty and assumption tracking
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from coprocessor.agents.narrative_agent import NarrativeAgent
from coprocessor.schemas.narrative import (
    NarrativeMemo,
    NarrativeClaim,
    EvidenceReference,
    MemoSection,
    MemoTemplate,
    MemoLength,
    MemoTemplateConfig,
)


class TestNarrativeAgentInitialization:
    """Tests for NarrativeAgent initialization."""

    def test_agent_initialization_default(self):
        """Test agent initialization with defaults."""
        agent = NarrativeAgent()

        assert agent.model == "claude-sonnet-4-20250514"
        assert agent.system_prompt is not None

    def test_agent_initialization_custom_model(self):
        """Test agent initialization with custom model."""
        agent = NarrativeAgent(model="claude-3-opus")

        assert agent.model == "claude-3-opus"

    def test_agent_has_system_prompt(self):
        """Test that agent has a system prompt."""
        agent = NarrativeAgent()

        assert len(agent.system_prompt) > 0
        # Should mention grounding requirement
        assert "evidence" in agent.system_prompt.lower()


class TestNarrativeAgentMemoBuilding:
    """Tests for memo building functionality."""

    @pytest.fixture
    def agent(self):
        """Create a NarrativeAgent instance."""
        return NarrativeAgent()

    def test_build_memo_from_valid_data(self, agent, sample_evidence_pack):
        """Test building memo from valid parsed data."""
        memo_data = {
            "title": "Test Memo",
            "sections": [
                {
                    "heading": "Situation",
                    "claims": [
                        {
                            "text": "Position exceeded limit",
                            "evidence_refs": ["sig_001"],
                        }
                    ],
                }
            ],
        }

        memo = agent._build_memo("dec_001", memo_data, sample_evidence_pack)

        assert isinstance(memo, NarrativeMemo)
        assert memo.decision_id == "dec_001"
        assert memo.title == "Test Memo"
        assert len(memo.sections) == 1
        assert len(memo.sections[0].claims) == 1

    def test_build_memo_evidence_type_mapping(self, agent, sample_evidence_pack):
        """Test that evidence types are correctly mapped."""
        memo_data = {
            "title": "Test",
            "sections": [
                {
                    "heading": "Test",
                    "claims": [
                        {
                            "text": "Claim with signal evidence",
                            "evidence_refs": ["sig_001"],
                        }
                    ],
                }
            ],
        }

        memo = agent._build_memo("dec_001", memo_data, sample_evidence_pack)

        # Should have found the evidence type from the pack
        ref = memo.sections[0].claims[0].evidence_refs[0]
        assert ref.evidence_type == "signal"

    def test_build_memo_unknown_evidence_ref(self, agent, sample_evidence_pack):
        """Test handling of unknown evidence references."""
        memo_data = {
            "title": "Test",
            "sections": [
                {
                    "heading": "Test",
                    "claims": [
                        {
                            "text": "Claim with unknown evidence",
                            "evidence_refs": ["unknown_id"],
                        }
                    ],
                }
            ],
        }

        memo = agent._build_memo("dec_001", memo_data, sample_evidence_pack)

        # Should still build but with unknown type
        ref = memo.sections[0].claims[0].evidence_refs[0]
        assert ref.evidence_type == "unknown"


class TestNarrativeAgentExcerptExtraction:
    """Tests for excerpt extraction from evidence."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    def test_extract_excerpt_signal(self, agent):
        """Test excerpt extraction from signal evidence."""
        evidence_item = {
            "type": "signal",
            "data": {"signal_type": "position_limit_breach"},
        }

        excerpt = agent._extract_excerpt(evidence_item)

        assert "Signal:" in excerpt
        assert "position_limit_breach" in excerpt

    def test_extract_excerpt_chosen_option(self, agent):
        """Test excerpt extraction from chosen option."""
        evidence_item = {
            "type": "chosen_option",
            "data": {"label": "Reduce Position"},
        }

        excerpt = agent._extract_excerpt(evidence_item)

        assert "Option:" in excerpt
        assert "Reduce Position" in excerpt

    def test_extract_excerpt_policy(self, agent):
        """Test excerpt extraction from policy."""
        evidence_item = {
            "type": "policy",
            "data": {"name": "Position Limit Policy"},
        }

        excerpt = agent._extract_excerpt(evidence_item)

        assert "Policy:" in excerpt
        assert "Position Limit Policy" in excerpt


class TestNarrativeAgentGroundingValidation:
    """Tests for grounding validation functionality."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    def test_validate_grounding_valid(self, agent, sample_evidence_pack):
        """Test validation of properly grounded memo."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Claim with valid evidence",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_001", evidence_type="signal"),
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

        errors = agent.validate_grounding(memo, sample_evidence_pack)

        assert len(errors) == 0

    def test_validate_grounding_invalid_ref(self, agent, sample_evidence_pack):
        """Test validation catches invalid evidence references."""
        sections = [
            MemoSection(
                heading="Test",
                claims=[
                    NarrativeClaim(
                        text="Claim with invalid evidence",
                        evidence_refs=[
                            EvidenceReference(evidence_id="nonexistent_id", evidence_type="unknown"),
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

        errors = agent.validate_grounding(memo, sample_evidence_pack)

        assert len(errors) > 0
        assert "nonexistent_id" in errors[0]


class TestNarrativeAgentMarkdownFormatting:
    """Tests for markdown formatting."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    def test_format_memo_markdown(self, agent):
        """Test formatting memo as markdown."""
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
                ],
            ),
        ]
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Position Limit Breach",
            sections=sections,
        )

        markdown = agent.format_memo_markdown(memo)

        assert "# Position Limit Breach" in markdown
        assert "## Situation" in markdown
        assert "[sig_001]" in markdown
        assert "Evidence References" in markdown

    def test_format_memo_includes_decision_id(self, agent):
        """Test that markdown includes decision ID."""
        memo = NarrativeMemo(
            decision_id="dec_test_123",
            title="Test",
            sections=[],
        )

        markdown = agent.format_memo_markdown(memo)

        assert "dec_test_123" in markdown


class TestNarrativeAgentDraftMemo:
    """Tests for draft_memo functionality (requires mocking LLM)."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent(api_key="test_key")

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_parses_json_response(self, mock_get_client, agent, sample_evidence_pack):
        """Test that draft_memo parses JSON response correctly."""
        # Mock LLM response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='''
        {
            "title": "Test Decision Summary",
            "sections": [
                {
                    "heading": "Overview",
                    "claims": [
                        {
                            "text": "The position exceeded the limit",
                            "evidence_refs": ["sig_001"]
                        }
                    ]
                }
            ]
        }
        ''')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync("dec_001", sample_evidence_pack)

        assert isinstance(memo, NarrativeMemo)
        assert memo.title == "Test Decision Summary"
        assert len(memo.sections) == 1

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_handles_markdown_wrapped_json(self, mock_get_client, agent, sample_evidence_pack):
        """Test that draft_memo handles JSON wrapped in markdown code blocks."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='''
        Here's the memo:
        ```json
        {
            "title": "Test",
            "sections": []
        }
        ```
        ''')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync("dec_001", sample_evidence_pack)

        assert memo.title == "Test"

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_invalid_json_raises(self, mock_get_client, agent, sample_evidence_pack):
        """Test that invalid JSON response raises error."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text="This is not valid JSON")]
        mock_client.messages.create.return_value = mock_response

        with pytest.raises(ValueError, match="Failed to parse"):
            agent.draft_memo_sync("dec_001", sample_evidence_pack)


class TestNarrativeAgentSafetyConstraints:
    """Tests for safety constraints on agent behavior."""

    def test_system_prompt_forbids_recommendations(self):
        """Test that system prompt forbids recommendations."""
        agent = NarrativeAgent()

        prompt = agent.system_prompt.lower()

        # Should mention that recommendations are forbidden
        assert "recommend" in prompt or "should" in prompt
        assert "never" in prompt or "do not" in prompt or "forbidden" in prompt

    def test_system_prompt_requires_grounding(self):
        """Test that system prompt requires evidence grounding."""
        agent = NarrativeAgent()

        prompt = agent.system_prompt.lower()

        # Should mention grounding requirement
        assert "evidence" in prompt
        assert ("must" in prompt or "required" in prompt or "every" in prompt)


# ============================================================================
# V1 TESTS: MULTI-TEMPLATE SUPPORT
# ============================================================================

class TestNarrativeAgentV1Templates:
    """Tests for NarrativeAgent v1 multi-template support."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    def test_get_available_templates_treasury(self, agent):
        """Test getting available templates for treasury pack."""
        templates = agent.get_available_templates("treasury")

        assert MemoTemplate.TREASURY_LIQUIDITY in templates
        assert MemoTemplate.TREASURY_POSITION in templates
        assert MemoTemplate.TREASURY_COUNTERPARTY in templates
        assert MemoTemplate.EXECUTIVE_SUMMARY in templates
        assert MemoTemplate.DECISION_BRIEF in templates

    def test_get_available_templates_wealth(self, agent):
        """Test getting available templates for wealth pack."""
        templates = agent.get_available_templates("wealth")

        assert MemoTemplate.WEALTH_SUITABILITY in templates
        assert MemoTemplate.WEALTH_PORTFOLIO in templates
        assert MemoTemplate.WEALTH_CLIENT in templates
        assert MemoTemplate.EXECUTIVE_SUMMARY in templates
        assert MemoTemplate.DECISION_BRIEF in templates

    def test_get_available_templates_unknown_pack(self, agent):
        """Test getting templates for unknown pack returns default."""
        templates = agent.get_available_templates("unknown_pack")

        # Should return at least decision_brief
        assert MemoTemplate.DECISION_BRIEF in templates

    def test_get_template_config_treasury_liquidity(self, agent):
        """Test getting treasury liquidity template config."""
        config = agent.get_template_config(MemoTemplate.TREASURY_LIQUIDITY)

        assert config is not None
        assert config.template_id == MemoTemplate.TREASURY_LIQUIDITY
        assert config.pack == "treasury"
        assert "liquidity" in config.name.lower()
        assert len(config.required_sections) > 0
        assert len(config.vocabulary_hints) > 0

    def test_get_template_config_wealth_suitability(self, agent):
        """Test getting wealth suitability template config."""
        config = agent.get_template_config(MemoTemplate.WEALTH_SUITABILITY)

        assert config is not None
        assert config.template_id == MemoTemplate.WEALTH_SUITABILITY
        assert config.pack == "wealth"
        assert "suitability" in config.name.lower()

    def test_template_config_has_length_guidelines(self, agent):
        """Test that template configs have length guidelines."""
        config = agent.get_template_config(MemoTemplate.TREASURY_LIQUIDITY)

        assert "short" in config.length_guidelines
        assert "standard" in config.length_guidelines
        assert "detailed" in config.length_guidelines

        # Short should have fewer sections than detailed
        assert config.length_guidelines["short"]["max_sections"] <= config.length_guidelines["detailed"]["max_sections"]


class TestNarrativeAgentV1TemplatePromptBuilding:
    """Tests for template prompt building functionality."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    def test_build_template_prompt_includes_name(self, agent):
        """Test that template prompt includes template name."""
        prompt = agent._build_template_prompt(
            MemoTemplate.TREASURY_LIQUIDITY,
            MemoLength.STANDARD,
            "treasury"
        )

        assert "Treasury Liquidity" in prompt

    def test_build_template_prompt_includes_sections(self, agent):
        """Test that template prompt includes required sections."""
        prompt = agent._build_template_prompt(
            MemoTemplate.TREASURY_LIQUIDITY,
            MemoLength.STANDARD,
            "treasury"
        )

        assert "Required sections" in prompt or "Current Position" in prompt

    def test_build_template_prompt_includes_vocabulary(self, agent):
        """Test that template prompt includes vocabulary hints."""
        prompt = agent._build_template_prompt(
            MemoTemplate.TREASURY_LIQUIDITY,
            MemoLength.STANDARD,
            "treasury"
        )

        assert "liquidity" in prompt.lower()

    def test_build_template_prompt_short_length(self, agent):
        """Test that short length has appropriate guidance."""
        prompt = agent._build_template_prompt(
            MemoTemplate.TREASURY_LIQUIDITY,
            MemoLength.SHORT,
            "treasury"
        )

        assert "SHORT" in prompt
        assert "essential" in prompt.lower() or "brief" in prompt.lower() or "1-2" in prompt

    def test_build_template_prompt_detailed_length(self, agent):
        """Test that detailed length has appropriate guidance."""
        prompt = agent._build_template_prompt(
            MemoTemplate.TREASURY_LIQUIDITY,
            MemoLength.DETAILED,
            "treasury"
        )

        assert "DETAILED" in prompt
        assert "comprehensive" in prompt.lower() or "context" in prompt.lower()


class TestNarrativeAgentV1TemplateValidation:
    """Tests for template validation."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_rejects_invalid_template_for_pack(self, mock_get_client, agent, sample_evidence_pack):
        """Test that draft_memo rejects templates not valid for pack."""
        # Treasury template should not be available for wealth pack
        with pytest.raises(ValueError, match="not available for pack"):
            agent.draft_memo_sync(
                "dec_001",
                sample_evidence_pack,
                template=MemoTemplate.TREASURY_LIQUIDITY,
                pack="wealth"
            )

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_accepts_valid_template_for_pack(self, mock_get_client, agent, sample_evidence_pack):
        """Test that draft_memo accepts valid templates for pack."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='''
        {
            "title": "Test",
            "sections": [
                {"heading": "Current Position", "claims": [{"text": "Test", "evidence_refs": ["sig_001"]}]}
            ],
            "uncertainties": [],
            "assumptions": []
        }
        ''')]
        mock_client.messages.create.return_value = mock_response

        # This should not raise
        memo = agent.draft_memo_sync(
            "dec_001",
            sample_evidence_pack,
            template=MemoTemplate.TREASURY_LIQUIDITY,
            pack="treasury"
        )

        assert memo is not None
        assert memo.template_used == "treasury_liquidity"


class TestNarrativeAgentV1LengthVariants:
    """Tests for length variant support."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_accepts_short_length(self, mock_get_client, agent, sample_evidence_pack):
        """Test that draft_memo accepts short length."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='{"title": "Test", "sections": [], "uncertainties": [], "assumptions": []}')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync(
            "dec_001",
            sample_evidence_pack,
            length=MemoLength.SHORT,
            pack="treasury"
        )

        assert memo.length == "short"

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_accepts_detailed_length(self, mock_get_client, agent, sample_evidence_pack):
        """Test that draft_memo accepts detailed length."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='{"title": "Test", "sections": [], "uncertainties": [], "assumptions": []}')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync(
            "dec_001",
            sample_evidence_pack,
            length=MemoLength.DETAILED,
            pack="treasury"
        )

        assert memo.length == "detailed"

    @patch.object(NarrativeAgent, '_get_client')
    def test_draft_memo_accepts_string_length(self, mock_get_client, agent, sample_evidence_pack):
        """Test that draft_memo accepts string for length."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='{"title": "Test", "sections": [], "uncertainties": [], "assumptions": []}')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync(
            "dec_001",
            sample_evidence_pack,
            length="short",  # String instead of enum
            pack="treasury"
        )

        assert memo.length == "short"


class TestNarrativeAgentV1UncertaintiesAssumptions:
    """Tests for uncertainty and assumption tracking."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    @patch.object(NarrativeAgent, '_get_client')
    def test_memo_includes_uncertainties(self, mock_get_client, agent, sample_evidence_pack):
        """Test that memo captures uncertainties from LLM response."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='''
        {
            "title": "Test",
            "sections": [],
            "uncertainties": ["Exact timing of the breach is unknown", "Market conditions may have changed"],
            "assumptions": []
        }
        ''')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync("dec_001", sample_evidence_pack, pack="treasury")

        assert len(memo.uncertainties) == 2
        assert "timing" in memo.uncertainties[0].lower()

    @patch.object(NarrativeAgent, '_get_client')
    def test_memo_includes_assumptions(self, mock_get_client, agent, sample_evidence_pack):
        """Test that memo captures assumptions from LLM response."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='''
        {
            "title": "Test",
            "sections": [],
            "uncertainties": [],
            "assumptions": ["Market will remain stable", "Counterparty will honor agreement"]
        }
        ''')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync("dec_001", sample_evidence_pack, pack="treasury")

        assert len(memo.assumptions) == 2
        assert "market" in memo.assumptions[0].lower()

    def test_format_memo_markdown_includes_uncertainties(self, agent):
        """Test that markdown formatting includes uncertainties."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=[],
            uncertainties=["Some uncertainty"],
            assumptions=[],
        )

        markdown = agent.format_memo_markdown(memo)

        assert "Uncertainties" in markdown
        assert "Some uncertainty" in markdown

    def test_format_memo_markdown_includes_assumptions(self, agent):
        """Test that markdown formatting includes assumptions."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=[],
            uncertainties=[],
            assumptions=["Some assumption"],
        )

        markdown = agent.format_memo_markdown(memo)

        assert "Assumptions" in markdown
        assert "Some assumption" in markdown


class TestNarrativeAgentV1TemplateSelection:
    """Tests for automatic template selection."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    def test_select_template_for_liquidity_breach(self, agent):
        """Test selecting template for liquidity signal."""
        exception_context = {"signal_type": "liquidity_threshold_breach"}

        template = agent.select_template_for_exception(exception_context, "treasury")

        assert template == MemoTemplate.TREASURY_LIQUIDITY

    def test_select_template_for_position_breach(self, agent):
        """Test selecting template for position signal."""
        exception_context = {"signal_type": "position_limit_breach"}

        template = agent.select_template_for_exception(exception_context, "treasury")

        assert template == MemoTemplate.TREASURY_POSITION

    def test_select_template_for_suitability_mismatch(self, agent):
        """Test selecting template for suitability signal."""
        exception_context = {"signal_type": "suitability_mismatch"}

        template = agent.select_template_for_exception(exception_context, "wealth")

        assert template == MemoTemplate.WEALTH_SUITABILITY

    def test_select_template_unknown_signal_returns_default(self, agent):
        """Test selecting template for unknown signal returns default."""
        exception_context = {"signal_type": "unknown_signal_type"}

        template = agent.select_template_for_exception(exception_context, "treasury")

        assert template == MemoTemplate.DECISION_BRIEF


class TestNarrativeAgentV1PackTracking:
    """Tests for pack tracking in memos."""

    @pytest.fixture
    def agent(self):
        return NarrativeAgent()

    @patch.object(NarrativeAgent, '_get_client')
    def test_memo_tracks_pack(self, mock_get_client, agent, sample_evidence_pack):
        """Test that memo tracks which pack was used."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.content = [Mock(text='{"title": "Test", "sections": [], "uncertainties": [], "assumptions": []}')]
        mock_client.messages.create.return_value = mock_response

        memo = agent.draft_memo_sync("dec_001", sample_evidence_pack, pack="wealth")

        assert memo.pack == "wealth"

    def test_format_memo_markdown_includes_pack(self, agent):
        """Test that markdown formatting includes pack."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=[],
            pack="treasury",
        )

        markdown = agent.format_memo_markdown(memo)

        assert "treasury" in markdown.lower()

    def test_format_memo_markdown_includes_template(self, agent):
        """Test that markdown formatting includes template."""
        memo = NarrativeMemo(
            decision_id="dec_001",
            title="Test",
            sections=[],
            template_used="treasury_liquidity",
        )

        markdown = agent.format_memo_markdown(memo)

        assert "treasury_liquidity" in markdown
