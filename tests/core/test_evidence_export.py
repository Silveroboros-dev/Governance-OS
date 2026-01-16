"""
Tests for evidence pack export functionality.

Tests HTML and PDF export formats, determinism, and security.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from core.models import EvidencePack
from core.services.evidence_renderer import EvidenceRenderer


class TestEvidenceRenderer:
    """Tests for EvidenceRenderer service."""

    @pytest.fixture
    def sample_evidence_pack(self):
        """Create a sample evidence pack for testing."""
        pack = EvidencePack(
            id=uuid4(),
            decision_id=uuid4(),
            content_hash="abc123def456" * 4,  # 64 char hash
            generated_at=datetime.now(timezone.utc),
            evidence={
                "decision": {
                    "id": str(uuid4()),
                    "chosen_option_id": "reduce_exposure",
                    "rationale": "Market conditions indicate high risk",
                    "assumptions": "Volatility expected to continue",
                    "decided_by": "treasury_ops@example.com",
                    "decided_at": "2026-01-15T10:30:00Z"
                },
                "exception": {
                    "id": str(uuid4()),
                    "title": "Position Limit Breach - BTC",
                    "severity": "high",
                    "context": {"asset": "BTC", "current_position": 125, "limit": 100},
                    "options": [
                        {"id": "reduce_exposure", "label": "Reduce Exposure", "description": "Sell excess position"},
                        {"id": "request_increase", "label": "Request Limit Increase", "description": "Submit for approval"},
                        {"id": "hedge_position", "label": "Hedge Position", "description": "Use derivatives"}
                    ],
                    "raised_at": "2026-01-15T09:00:00Z",
                    "resolved_at": "2026-01-15T10:30:00Z",
                    "fingerprint": "btc_position_breach_20260115"
                },
                "evaluation": {
                    "id": str(uuid4()),
                    "result": "exception_raised",
                    "details": {"breach_amount": 25, "breach_percentage": 25},
                    "evaluated_at": "2026-01-15T09:00:00Z",
                    "input_hash": "eval_input_hash_123"
                },
                "policy": {
                    "id": str(uuid4()),
                    "name": "Position Limits Policy",
                    "pack": "treasury",
                    "description": "Enforces position limits across asset classes",
                    "version": {
                        "id": str(uuid4()),
                        "version_number": 3,
                        "rule_definition": {"max_position_pct": 10},
                        "valid_from": "2026-01-01T00:00:00Z",
                        "valid_to": None
                    }
                },
                "signals": [
                    {
                        "id": str(uuid4()),
                        "signal_type": "position_update",
                        "payload": {"asset": "BTC", "quantity": 125},
                        "source": "trading_system",
                        "reliability": "high",
                        "observed_at": "2026-01-15T08:55:00Z",
                        "metadata": {}
                    },
                    {
                        "id": str(uuid4()),
                        "signal_type": "limit_check",
                        "payload": {"asset": "BTC", "limit": 100},
                        "source": "risk_system",
                        "reliability": "high",
                        "observed_at": "2026-01-15T08:50:00Z",
                        "metadata": {}
                    }
                ],
                "audit_trail": [
                    {
                        "id": str(uuid4()),
                        "event_type": "evaluation_completed",
                        "aggregate_type": "evaluation",
                        "aggregate_id": str(uuid4()),
                        "event_data": {},
                        "actor": "system",
                        "occurred_at": "2026-01-15T09:00:00Z"
                    },
                    {
                        "id": str(uuid4()),
                        "event_type": "exception_raised",
                        "aggregate_type": "exception",
                        "aggregate_id": str(uuid4()),
                        "event_data": {},
                        "actor": "system",
                        "occurred_at": "2026-01-15T09:00:01Z"
                    },
                    {
                        "id": str(uuid4()),
                        "event_type": "decision_recorded",
                        "aggregate_type": "decision",
                        "aggregate_id": str(uuid4()),
                        "event_data": {},
                        "actor": "treasury_ops@example.com",
                        "occurred_at": "2026-01-15T10:30:00Z"
                    }
                ],
                "metadata": {
                    "pack_version": "1.0",
                    "generated_for_decision": str(uuid4())
                }
            }
        )
        return pack

    def test_render_html_includes_all_sections(self, sample_evidence_pack):
        """HTML output contains all required sections."""
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        # Check all major sections present
        assert "Executive Summary" in html
        assert "Policy Applied" in html
        assert "Contributing Signals" in html
        assert "Exception Details" in html
        assert "Decision Record" in html
        assert "Audit Trail" in html
        assert "Integrity Verification" in html

    def test_render_html_includes_content_hash(self, sample_evidence_pack):
        """HTML includes the content hash for verification."""
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        assert sample_evidence_pack.content_hash in html

    def test_render_html_includes_decision_details(self, sample_evidence_pack):
        """HTML includes decision rationale and chosen option."""
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        assert "Market conditions indicate high risk" in html
        assert "Reduce Exposure" in html
        assert "CHOSEN" in html

    def test_render_html_includes_policy_info(self, sample_evidence_pack):
        """HTML includes policy name and version."""
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        assert "Position Limits Policy" in html
        assert "treasury" in html

    def test_render_html_includes_signals(self, sample_evidence_pack):
        """HTML includes signal information."""
        renderer = EvidenceRenderer()
        html = renderer.render_html(sample_evidence_pack)

        assert "position_update" in html
        assert "trading_system" in html
        assert "Contributing Signals (2)" in html

    def test_render_html_deterministic(self, sample_evidence_pack):
        """Same evidence pack produces identical HTML."""
        renderer = EvidenceRenderer()
        html1 = renderer.render_html(sample_evidence_pack)
        html2 = renderer.render_html(sample_evidence_pack)

        assert html1 == html2

    def test_render_html_escapes_xss(self):
        """User content is properly escaped to prevent XSS."""
        pack = EvidencePack(
            id=uuid4(),
            decision_id=uuid4(),
            content_hash="x" * 64,
            generated_at=datetime.now(timezone.utc),
            evidence={
                "decision": {
                    "id": str(uuid4()),
                    "chosen_option_id": "opt1",
                    "rationale": "<script>alert('xss')</script>",
                    "assumptions": "<img src=x onerror=alert('xss')>",
                    "decided_by": "user",
                    "decided_at": "2026-01-15T10:00:00Z"
                },
                "exception": {
                    "id": str(uuid4()),
                    "title": "<b>Bold Title</b>",
                    "severity": "high",
                    "context": {},
                    "options": [{"id": "opt1", "label": "Option", "description": ""}],
                    "raised_at": "2026-01-15T09:00:00Z",
                    "resolved_at": None,
                    "fingerprint": "test"
                },
                "evaluation": {
                    "id": str(uuid4()),
                    "result": "exception_raised",
                    "details": {},
                    "evaluated_at": "2026-01-15T09:00:00Z",
                    "input_hash": "hash"
                },
                "policy": {
                    "id": str(uuid4()),
                    "name": "Test Policy",
                    "pack": "treasury",
                    "description": "",
                    "version": {
                        "id": str(uuid4()),
                        "version_number": 1,
                        "rule_definition": {},
                        "valid_from": "2026-01-01T00:00:00Z",
                        "valid_to": None
                    }
                },
                "signals": [],
                "audit_trail": [],
                "metadata": {}
            }
        )

        renderer = EvidenceRenderer()
        html = renderer.render_html(pack)

        # Script tags should be escaped (not executable)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

        # Image tag should be escaped (not executable)
        assert "<img src=" not in html
        assert "&lt;img" in html

    def test_render_html_handles_null_fields(self):
        """Template handles null optional fields gracefully."""
        pack = EvidencePack(
            id=uuid4(),
            decision_id=uuid4(),
            content_hash="x" * 64,
            generated_at=datetime.now(timezone.utc),
            evidence={
                "decision": {
                    "id": str(uuid4()),
                    "chosen_option_id": "opt1",
                    "rationale": None,  # Null rationale
                    "assumptions": None,  # Null assumptions
                    "decided_by": None,
                    "decided_at": "2026-01-15T10:00:00Z"
                },
                "exception": {
                    "id": str(uuid4()),
                    "title": "Test Exception",
                    "severity": "low",
                    "context": None,  # Null context
                    "options": [{"id": "opt1", "label": "Option", "description": ""}],
                    "raised_at": "2026-01-15T09:00:00Z",
                    "resolved_at": None,
                    "fingerprint": "test"
                },
                "evaluation": {
                    "id": str(uuid4()),
                    "result": "exception_raised",
                    "details": {},
                    "evaluated_at": "2026-01-15T09:00:00Z",
                    "input_hash": "hash"
                },
                "policy": {
                    "id": str(uuid4()),
                    "name": "Test Policy",
                    "pack": "treasury",
                    "description": "",
                    "version": {
                        "id": str(uuid4()),
                        "version_number": 1,
                        "rule_definition": {},
                        "valid_from": "2026-01-01T00:00:00Z",
                        "valid_to": None
                    }
                },
                "signals": [],
                "audit_trail": [],
                "metadata": {}
            }
        )

        renderer = EvidenceRenderer()
        # Should not raise an exception
        html = renderer.render_html(pack)

        # Should show fallback text for null rationale
        assert "No rationale provided" in html

    def test_signals_sorted_by_observed_at(self, sample_evidence_pack):
        """Signals appear in chronological order."""
        renderer = EvidenceRenderer()
        context = renderer._prepare_context(sample_evidence_pack)

        # Signals should be sorted by observed_at
        signals = context["signals"]
        assert len(signals) == 2

        # limit_check (08:50) should come before position_update (08:55)
        assert signals[0]["signal_type"] == "limit_check"
        assert signals[1]["signal_type"] == "position_update"

    def test_audit_trail_sorted_by_occurred_at(self, sample_evidence_pack):
        """Audit trail appears in chronological order."""
        renderer = EvidenceRenderer()
        context = renderer._prepare_context(sample_evidence_pack)

        audit_trail = context["audit_trail"]
        assert len(audit_trail) == 3

        # Events should be in order
        assert audit_trail[0]["event_type"] == "evaluation_completed"
        assert audit_trail[1]["event_type"] == "exception_raised"
        assert audit_trail[2]["event_type"] == "decision_recorded"

    def test_resolve_chosen_option(self, sample_evidence_pack):
        """Chosen option is resolved to full option details."""
        renderer = EvidenceRenderer()
        context = renderer._prepare_context(sample_evidence_pack)

        chosen = context["chosen_option"]
        assert chosen["id"] == "reduce_exposure"
        assert chosen["label"] == "Reduce Exposure"
        assert chosen["description"] == "Sell excess position"

    def test_resolve_chosen_option_fallback(self):
        """Unknown option ID falls back gracefully."""
        pack = EvidencePack(
            id=uuid4(),
            decision_id=uuid4(),
            content_hash="x" * 64,
            generated_at=datetime.now(timezone.utc),
            evidence={
                "decision": {
                    "chosen_option_id": "unknown_option"
                },
                "exception": {
                    "options": [{"id": "other", "label": "Other", "description": ""}]
                },
                "evaluation": {},
                "policy": {},
                "signals": [],
                "audit_trail": [],
                "metadata": {}
            }
        )

        renderer = EvidenceRenderer()
        context = renderer._prepare_context(pack)

        # Should fallback to using the ID as label
        chosen = context["chosen_option"]
        assert chosen["id"] == "unknown_option"
        assert chosen["label"] == "unknown_option"


class TestEvidenceGeneratorExport:
    """Tests for EvidenceGenerator.export_pack() method."""

    @pytest.fixture
    def mock_evidence_pack(self):
        """Create a mock evidence pack for generator tests."""
        return EvidencePack(
            id=uuid4(),
            decision_id=uuid4(),
            content_hash="abc123def456" * 4,
            generated_at=datetime.now(timezone.utc),
            evidence={
                "decision": {"id": str(uuid4()), "rationale": "Test"},
                "exception": {"title": "Test Exception", "severity": "high", "options": []},
                "evaluation": {},
                "policy": {"name": "Test Policy"},
                "signals": [],
                "audit_trail": [],
                "metadata": {}
            }
        )

    def test_export_json_format(self, mock_evidence_pack):
        """JSON export returns valid JSON bytes."""
        import json

        # Mock the database query by creating a mock generator
        class MockSession:
            def __init__(self, pack):
                self._pack = pack

            def query(self, model):
                return self

            def filter(self, *args):
                return self

            def first(self):
                return self._pack

        from core.services.evidence_generator import EvidenceGenerator
        generator = EvidenceGenerator(MockSession(mock_evidence_pack))

        result = generator.export_pack(mock_evidence_pack.id, format="json")

        assert isinstance(result, bytes)
        # Should be valid JSON
        parsed = json.loads(result.decode("utf-8"))
        assert "decision" in parsed
        assert "exception" in parsed

    def test_export_html_format(self, mock_evidence_pack):
        """HTML export returns HTML bytes."""

        class MockSession:
            def __init__(self, pack):
                self._pack = pack

            def query(self, model):
                return self

            def filter(self, *args):
                return self

            def first(self):
                return self._pack

        from core.services.evidence_generator import EvidenceGenerator
        generator = EvidenceGenerator(MockSession(mock_evidence_pack))

        result = generator.export_pack(mock_evidence_pack.id, format="html")

        assert isinstance(result, bytes)
        html = result.decode("utf-8")
        assert "<!DOCTYPE html>" in html
        assert "Evidence Pack" in html

    def test_export_invalid_format_raises(self, mock_evidence_pack):
        """Invalid format raises ValueError."""

        class MockSession:
            def __init__(self, pack):
                self._pack = pack

            def query(self, model):
                return self

            def filter(self, *args):
                return self

            def first(self):
                return self._pack

        from core.services.evidence_generator import EvidenceGenerator
        generator = EvidenceGenerator(MockSession(mock_evidence_pack))

        with pytest.raises(ValueError, match="not supported"):
            generator.export_pack(mock_evidence_pack.id, format="xlsx")

    def test_export_pack_not_found_raises(self):
        """Missing pack raises ValueError."""

        class MockSession:
            def query(self, model):
                return self

            def filter(self, *args):
                return self

            def first(self):
                return None

        from core.services.evidence_generator import EvidenceGenerator
        generator = EvidenceGenerator(MockSession())

        with pytest.raises(ValueError, match="not found"):
            generator.export_pack(uuid4(), format="json")
