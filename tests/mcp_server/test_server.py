"""
Tests for MCP Server - Read-only tools for governance kernel.

Note: These tests mock the database layer since we're testing
the tool logic, not database connectivity.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Skip all tests in this module if mcp library is not installed
try:
    import mcp
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not MCP_AVAILABLE,
    reason="MCP library not installed"
)


class TestMCPServerInitialization:
    """Tests for MCP server initialization."""

    def test_server_import(self):
        """Test that server module imports correctly."""
        from mcp_server.server import mcp, create_server

        assert mcp is not None
        assert create_server is not None

    def test_server_name(self):
        """Test server is named correctly."""
        from mcp_server.server import mcp

        assert mcp.name == "governance-os"


class TestGetOpenExceptions:
    """Tests for get_open_exceptions tool."""

    @patch('mcp_server.server.get_db_session')
    def test_get_open_exceptions_basic(self, mock_get_session):
        """Test basic exception retrieval."""
        from mcp_server.server import get_open_exceptions

        # Mock database session and query
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock exception objects
        mock_exception = Mock()
        mock_exception.id = "exc-001"
        mock_exception.title = "Test Exception"
        mock_exception.severity = Mock(value="high")
        mock_exception.status = Mock(value="open")
        mock_exception.raised_at = datetime(2025, 1, 15, 10, 0, 0)
        mock_exception.context = {"asset": "BTC"}
        mock_exception.policy_id = "policy-001"

        # Setup query chain
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_exception]

        result = get_open_exceptions()

        assert len(result) == 1
        assert result[0]["id"] == "exc-001"
        assert result[0]["title"] == "Test Exception"
        assert result[0]["severity"] == "high"

    @patch('mcp_server.server.get_db_session')
    def test_get_open_exceptions_with_filters(self, mock_get_session):
        """Test exception retrieval with filters."""
        from mcp_server.server import get_open_exceptions

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = get_open_exceptions(severity="critical", limit=10)

        assert result == []
        # Verify filter was applied
        assert mock_query.filter.called

    @patch('mcp_server.server.get_db_session')
    def test_get_open_exceptions_error_handling(self, mock_get_session):
        """Test error handling in exception retrieval."""
        from mcp_server.server import get_open_exceptions

        mock_get_session.side_effect = Exception("Database error")

        result = get_open_exceptions()

        assert len(result) == 1
        assert "error" in result[0]


class TestGetExceptionDetail:
    """Tests for get_exception_detail tool."""

    @patch('mcp_server.server.get_db_session')
    def test_get_exception_detail_not_found(self, mock_get_session):
        """Test handling of non-existent exception."""
        from mcp_server.server import get_exception_detail

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = get_exception_detail("nonexistent-id")

        assert "error" in result
        assert "not found" in result["error"].lower()


class TestGetPolicies:
    """Tests for get_policies tool."""

    @patch('mcp_server.server.get_db_session')
    def test_get_policies_basic(self, mock_get_session):
        """Test basic policy retrieval."""
        from mcp_server.server import get_policies

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock policy
        mock_policy = Mock()
        mock_policy.id = "policy-001"
        mock_policy.name = "Position Limit Policy"
        mock_policy.description = "Test policy"
        mock_policy.is_active = True
        mock_policy.created_at = datetime(2025, 1, 1)

        # Mock version
        mock_version = Mock()
        mock_version.id = "version-001"
        mock_version.version_number = 1
        mock_version.rule_definition = {"type": "threshold_breach"}
        mock_version.effective_from = datetime(2025, 1, 1)

        # Setup queries
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_policy]
        mock_query.first.return_value = mock_version

        result = get_policies()

        assert len(result) == 1
        assert result[0]["id"] == "policy-001"
        assert result[0]["name"] == "Position Limit Policy"

    @patch('mcp_server.server.get_db_session')
    def test_get_policies_with_versions(self, mock_get_session):
        """Test policy retrieval with version history."""
        from mcp_server.server import get_policies

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_policy = Mock()
        mock_policy.id = "policy-001"
        mock_policy.name = "Test Policy"
        mock_policy.description = "Test"
        mock_policy.is_active = True
        mock_policy.created_at = datetime(2025, 1, 1)

        mock_version = Mock()
        mock_version.id = "v1"
        mock_version.version_number = 1
        mock_version.is_current = True
        mock_version.rule_definition = {}
        mock_version.effective_from = datetime(2025, 1, 1)
        mock_version.change_reason = "Initial"

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.side_effect = [[mock_policy], [mock_version]]
        mock_query.first.return_value = mock_version

        result = get_policies(include_versions=True)

        assert len(result) == 1


class TestGetEvidencePack:
    """Tests for get_evidence_pack tool."""

    @patch('mcp_server.server.get_db_session')
    def test_get_evidence_pack_not_found(self, mock_get_session):
        """Test handling of non-existent decision."""
        from mcp_server.server import get_evidence_pack

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None

        result = get_evidence_pack("nonexistent-id")

        assert "error" in result
        assert "not found" in result["error"].lower()

    @patch('mcp_server.server.get_db_session')
    def test_get_evidence_pack_structure(self, mock_get_session):
        """Test evidence pack has correct structure."""
        from mcp_server.server import get_evidence_pack

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock decision
        mock_decision = Mock()
        mock_decision.id = "dec-001"
        mock_decision.decided_at = datetime(2025, 1, 15)
        mock_decision.decided_by = "user@example.com"
        mock_decision.rationale = "Test rationale"
        mock_decision.assumptions = "Test assumptions"
        mock_decision.chosen_option_id = None
        mock_decision.exception_id = None

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_decision
        mock_query.filter.return_value.order_by.return_value.all.return_value = []

        result = get_evidence_pack("dec-001")

        assert "evidence_pack_id" in result
        assert "decision" in result
        assert "evidence_items" in result
        assert result["decision"]["id"] == "dec-001"


class TestSearchDecisions:
    """Tests for search_decisions tool."""

    @patch('mcp_server.server.get_db_session')
    def test_search_decisions_basic(self, mock_get_session):
        """Test basic decision search."""
        from mcp_server.server import search_decisions

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_decision = Mock()
        mock_decision.id = "dec-001"
        mock_decision.decided_at = datetime(2025, 1, 15)
        mock_decision.decided_by = "user@example.com"
        mock_decision.rationale = "Test rationale"
        mock_decision.exception_id = "exc-001"

        mock_exception = Mock()
        mock_exception.id = "exc-001"
        mock_exception.title = "Test Exception"
        mock_exception.severity = Mock(value="high")

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_decision]
        mock_query.first.return_value = mock_exception

        result = search_decisions()

        assert len(result) == 1
        assert result[0]["id"] == "dec-001"

    @patch('mcp_server.server.get_db_session')
    def test_search_decisions_with_date_filter(self, mock_get_session):
        """Test decision search with date filters."""
        from mcp_server.server import search_decisions

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = search_decisions(
            from_date="2025-01-01T00:00:00",
            to_date="2025-01-31T23:59:59"
        )

        assert result == []
        # Verify filters were applied
        assert mock_query.filter.call_count >= 2


class TestGetRecentSignals:
    """Tests for get_recent_signals tool."""

    @patch('mcp_server.server.get_db_session')
    def test_get_recent_signals_basic(self, mock_get_session):
        """Test basic signal retrieval."""
        from mcp_server.server import get_recent_signals

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_signal = Mock()
        mock_signal.id = "sig-001"
        mock_signal.signal_type = "position_limit_breach"
        mock_signal.source = "test_system"
        mock_signal.payload = {"asset": "BTC"}
        mock_signal.timestamp = datetime(2025, 1, 15)
        mock_signal.reliability = 0.95

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_signal]

        result = get_recent_signals()

        assert len(result) == 1
        assert result[0]["id"] == "sig-001"
        assert result[0]["signal_type"] == "position_limit_breach"

    @patch('mcp_server.server.get_db_session')
    def test_get_recent_signals_with_filters(self, mock_get_session):
        """Test signal retrieval with type and source filters."""
        from mcp_server.server import get_recent_signals

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = get_recent_signals(
            signal_type="position_limit_breach",
            source="test_system",
            limit=10
        )

        assert result == []
        # Verify filters were applied
        assert mock_query.filter.call_count >= 2


class TestMCPServerSafety:
    """Tests for MCP server safety constraints."""

    def test_no_write_tools_exposed(self):
        """Verify no write tools are exposed in v0."""
        from mcp_server.server import mcp

        # Get all registered tools
        # Note: This depends on FastMCP implementation
        # We're checking that write operations are not available

        # These tool names should NOT exist
        forbidden_tools = [
            "create_decision",
            "update_policy",
            "delete_exception",
            "modify_signal",
        ]

        # The mcp object should not have these methods
        for tool_name in forbidden_tools:
            # Check the server doesn't expose these
            assert not hasattr(mcp, tool_name), f"Write tool {tool_name} should not be exposed"

    def test_server_instructions_mention_read_only(self):
        """Verify server instructions indicate read-only."""
        from mcp_server.server import mcp

        assert "read-only" in mcp.instructions.lower() or "read only" in mcp.instructions.lower()
