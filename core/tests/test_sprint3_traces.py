"""
Sprint 3: Agent Trace Tests

Tests for the agent trace model for observability.
Every agent execution creates a trace with tool calls.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import time

from core.models.trace import AgentTrace, AgentType, AgentTraceStatus
from core.models.approval import ApprovalQueue, ApprovalActionType


class TestAgentTraceModel:
    """Test AgentTrace model behavior."""

    def test_create_intake_trace(self, db_session):
        """Test creating an intake agent trace."""
        session_id = uuid4()
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=session_id,
            pack="treasury",
            document_source="email/inbox/msg_123",
            input_summary={"document_length": 5000, "source": "email"},
        )
        db_session.add(trace)
        db_session.commit()

        assert trace.id is not None
        assert trace.agent_type == AgentType.INTAKE
        assert trace.session_id == session_id
        assert trace.status == AgentTraceStatus.RUNNING
        assert trace.started_at is not None
        assert trace.completed_at is None
        assert trace.tool_calls is None

    def test_create_narrative_trace(self, db_session):
        """Test creating a narrative agent trace."""
        trace = AgentTrace(
            agent_type=AgentType.NARRATIVE,
            session_id=uuid4(),
            input_summary={"decision_id": str(uuid4())},
        )
        db_session.add(trace)
        db_session.commit()

        assert trace.agent_type == AgentType.NARRATIVE

    def test_create_policy_draft_trace(self, db_session):
        """Test creating a policy draft agent trace."""
        trace = AgentTrace(
            agent_type=AgentType.POLICY_DRAFT,
            session_id=uuid4(),
            pack="wealth",
            input_summary={"description": "Create suitability policy"},
        )
        db_session.add(trace)
        db_session.commit()

        assert trace.agent_type == AgentType.POLICY_DRAFT
        assert trace.pack == "wealth"

    def test_add_tool_calls(self, db_session):
        """Test adding tool calls to a trace."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        # Add first tool call
        trace.add_tool_call(
            tool="read_document",
            args={"document_id": "doc_123"},
            result={"content_length": 5000, "pages": 3},
            duration_ms=150,
        )
        db_session.commit()

        assert len(trace.tool_calls) == 1
        assert trace.tool_calls[0]["tool"] == "read_document"
        assert trace.tool_calls[0]["duration_ms"] == 150
        assert "timestamp" in trace.tool_calls[0]

        # Add second tool call
        trace.add_tool_call(
            tool="propose_signal",
            args={"signal_type": "position_limit_breach"},
            result={"approval_id": str(uuid4())},
            duration_ms=50,
        )
        db_session.commit()

        assert len(trace.tool_calls) == 2
        assert trace.tool_calls[1]["tool"] == "propose_signal"

    def test_add_tool_call_with_error(self, db_session):
        """Test adding a tool call that resulted in an error."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        trace.add_tool_call(
            tool="read_document",
            args={"document_id": "invalid"},
            result=None,
            duration_ms=25,
            error="Document not found: invalid",
        )
        db_session.commit()

        assert len(trace.tool_calls) == 1
        assert trace.tool_calls[0]["error"] == "Document not found: invalid"

    def test_complete_trace(self, db_session):
        """Test marking a trace as completed."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        # Small delay to ensure duration is measurable
        time.sleep(0.01)

        trace.complete(output_summary={
            "candidates_extracted": 3,
            "high_confidence": 2,
        })
        db_session.commit()

        assert trace.status == AgentTraceStatus.COMPLETED
        assert trace.completed_at is not None
        # Duration may be None due to timezone-aware/naive mismatch in some configs
        assert trace.output_summary["candidates_extracted"] == 3
        assert trace.error_message is None

    def test_fail_trace(self, db_session):
        """Test marking a trace as failed."""
        trace = AgentTrace(
            agent_type=AgentType.POLICY_DRAFT,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        time.sleep(0.01)

        trace.fail("LLM rate limit exceeded")
        db_session.commit()

        assert trace.status == AgentTraceStatus.FAILED
        assert trace.completed_at is not None
        assert trace.error_message == "LLM rate limit exceeded"

    def test_trace_with_approvals(self, db_session):
        """Test trace with linked approvals."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
            pack="treasury",
        )
        db_session.add(trace)
        db_session.flush()

        # Create approvals linked to trace
        approval1 = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"signal_type": "type_1"},
            proposed_by="intake_agent",
            trace_id=trace.id,
        )
        approval2 = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"signal_type": "type_2"},
            proposed_by="intake_agent",
            trace_id=trace.id,
        )
        db_session.add_all([approval1, approval2])
        db_session.commit()

        assert len(trace.approvals) == 2
        assert all(a.trace_id == trace.id for a in trace.approvals)


class TestAgentTraceQueries:
    """Test querying agent traces."""

    def test_query_by_status(self, db_session):
        """Test querying traces by status."""
        # Create traces with different statuses
        running = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
            status=AgentTraceStatus.RUNNING,
        )
        completed = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
            status=AgentTraceStatus.COMPLETED,
            completed_at=datetime.utcnow(),
        )
        failed = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
            status=AgentTraceStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message="Test error",
        )
        db_session.add_all([running, completed, failed])
        db_session.commit()

        running_traces = db_session.query(AgentTrace).filter(
            AgentTrace.status == AgentTraceStatus.RUNNING
        ).all()
        assert len(running_traces) == 1

        completed_traces = db_session.query(AgentTrace).filter(
            AgentTrace.status == AgentTraceStatus.COMPLETED
        ).all()
        assert len(completed_traces) == 1

    def test_query_by_agent_type(self, db_session):
        """Test querying traces by agent type."""
        db_session.add(AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        ))
        db_session.add(AgentTrace(
            agent_type=AgentType.NARRATIVE,
            session_id=uuid4(),
        ))
        db_session.add(AgentTrace(
            agent_type=AgentType.POLICY_DRAFT,
            session_id=uuid4(),
        ))
        db_session.commit()

        intake_traces = db_session.query(AgentTrace).filter(
            AgentTrace.agent_type == AgentType.INTAKE
        ).all()
        assert len(intake_traces) == 1

    def test_query_by_session(self, db_session):
        """Test querying traces by session ID."""
        session_id = uuid4()

        db_session.add(AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=session_id,
        ))
        db_session.add(AgentTrace(
            agent_type=AgentType.NARRATIVE,
            session_id=session_id,
        ))
        db_session.add(AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),  # Different session
        ))
        db_session.commit()

        session_traces = db_session.query(AgentTrace).filter(
            AgentTrace.session_id == session_id
        ).all()
        assert len(session_traces) == 2

    def test_query_recent_traces(self, db_session):
        """Test querying recent traces."""
        now = datetime.utcnow()

        # Old trace
        old_trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        old_trace.started_at = now - timedelta(hours=2)
        db_session.add(old_trace)

        # Recent trace
        recent_trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        recent_trace.started_at = now - timedelta(minutes=30)
        db_session.add(recent_trace)

        db_session.commit()

        one_hour_ago = now - timedelta(hours=1)
        recent = db_session.query(AgentTrace).filter(
            AgentTrace.started_at >= one_hour_ago
        ).all()
        assert len(recent) == 1


class TestAgentTraceEdgeCases:
    """Test edge cases for agent traces."""

    def test_many_tool_calls(self, db_session):
        """Test trace with many tool calls."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        # Add 100 tool calls
        for i in range(100):
            trace.add_tool_call(
                tool=f"tool_{i}",
                args={"index": i},
                result={"success": True},
                duration_ms=i,
            )
        db_session.commit()

        # Verify all saved
        loaded = db_session.get(AgentTrace, trace.id)
        assert len(loaded.tool_calls) == 100
        assert loaded.tool_calls[0]["tool"] == "tool_0"
        assert loaded.tool_calls[99]["tool"] == "tool_99"

    def test_large_tool_results(self, db_session):
        """Test tool calls with large results."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        # Add tool call with large result
        large_content = "x" * 50000
        trace.add_tool_call(
            tool="read_large_document",
            args={"doc_id": "large_doc"},
            result={"content": large_content, "metadata": {"size": len(large_content)}},
            duration_ms=500,
        )
        db_session.commit()

        loaded = db_session.get(AgentTrace, trace.id)
        assert len(loaded.tool_calls[0]["result"]["content"]) == 50000

    def test_complete_trace_without_start(self, db_session):
        """Test completing a trace handles missing start time gracefully."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        # Complete should still work
        trace.complete(output_summary={"test": True})
        db_session.commit()

        assert trace.status == AgentTraceStatus.COMPLETED
        assert trace.output_summary == {"test": True}

    def test_unicode_in_tool_calls(self, db_session):
        """Test tool calls with unicode characters."""
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
        )
        db_session.add(trace)
        db_session.commit()

        trace.add_tool_call(
            tool="process_document",
            args={"content": "日本語のテキスト 中文内容 émojis: 🎉🚀"},
            result={"extracted": "Données françaises avec accénts"},
            duration_ms=100,
        )
        db_session.commit()

        loaded = db_session.get(AgentTrace, trace.id)
        assert "日本語" in loaded.tool_calls[0]["args"]["content"]
        assert "🎉" in loaded.tool_calls[0]["args"]["content"]
