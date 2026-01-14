"""
Tests for NarrativeAgent - AI agent that drafts grounded memos.
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
