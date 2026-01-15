"""
AgentTrace model.

Sprint 3: Observability for agent executions.
Every agent invocation creates a trace with tool calls and outcomes.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Integer, Text, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from core.database import Base


class AgentType(str, PyEnum):
    """Types of agents in the coprocessor layer."""
    INTAKE = "intake"            # IntakeAgent: Extract signals from documents
    NARRATIVE = "narrative"      # NarrativeAgent: Generate evidence-grounded narratives
    POLICY_DRAFT = "policy_draft"  # PolicyDraftAgent: Generate draft policies


class AgentTraceStatus(str, PyEnum):
    """Status of agent execution."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentTrace(Base):
    """
    AgentTrace: Observability record for agent executions.

    Provides complete visibility into:
    - What inputs the agent received
    - Which tools were called and their results
    - What outputs were produced
    - Any errors that occurred

    Used by the Trace Viewer UI for debugging and audit.
    """
    __tablename__ = "agent_traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Agent identification
    agent_type = Column(
        SQLEnum(AgentType, name="agent_type",
                values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    session_id = Column(UUID(as_uuid=True), nullable=False)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_duration_ms = Column(Integer, nullable=True)

    # Status
    status = Column(
        SQLEnum(AgentTraceStatus, name="agent_trace_status",
                values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AgentTraceStatus.RUNNING
    )

    # Input/output summaries (for list views)
    input_summary = Column(JSONB, nullable=True)
    output_summary = Column(JSONB, nullable=True)

    # Detailed tool call log
    # Each entry: {tool: str, args: dict, result: any, duration_ms: int, error: str?}
    tool_calls = Column(ARRAY(JSONB), nullable=True)

    # Error details if failed
    error_message = Column(Text, nullable=True)

    # Context
    pack = Column(String(100), nullable=True)  # treasury/wealth
    document_source = Column(String(500), nullable=True)  # For intake agent

    # Relationships
    approvals = relationship("ApprovalQueue", back_populates="trace")

    __table_args__ = (
        Index("idx_agent_traces_session", "session_id"),
        Index("idx_agent_traces_status", "status"),
        Index("idx_agent_traces_agent_type", "agent_type"),
        Index("idx_agent_traces_started_at", "started_at"),
    )

    def __repr__(self):
        return f"<AgentTrace(id={self.id}, type='{self.agent_type.value}', status='{self.status.value}')>"

    def add_tool_call(
        self,
        tool: str,
        args: Dict[str, Any],
        result: Any,
        duration_ms: int,
        error: Optional[str] = None
    ):
        """Add a tool call to the trace."""
        call = {
            "tool": tool,
            "args": args,
            "result": result,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        if error:
            call["error"] = error

        if self.tool_calls is None:
            self.tool_calls = []
        self.tool_calls = self.tool_calls + [call]

    def complete(self, output_summary: Optional[Dict[str, Any]] = None):
        """Mark trace as completed successfully."""
        self.status = AgentTraceStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            try:
                # Handle timezone-aware/naive datetime comparison
                started = self.started_at.replace(tzinfo=None) if self.started_at.tzinfo else self.started_at
                completed = self.completed_at.replace(tzinfo=None) if hasattr(self.completed_at, 'tzinfo') and self.completed_at.tzinfo else self.completed_at
                self.total_duration_ms = int((completed - started).total_seconds() * 1000)
            except (AttributeError, TypeError):
                self.total_duration_ms = None
        if output_summary:
            self.output_summary = output_summary

    def fail(self, error_message: str):
        """Mark trace as failed."""
        self.status = AgentTraceStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            try:
                # Handle timezone-aware/naive datetime comparison
                started = self.started_at.replace(tzinfo=None) if self.started_at.tzinfo else self.started_at
                completed = self.completed_at.replace(tzinfo=None) if hasattr(self.completed_at, 'tzinfo') and self.completed_at.tzinfo else self.completed_at
                self.total_duration_ms = int((completed - started).total_seconds() * 1000)
            except (AttributeError, TypeError):
                self.total_duration_ms = None
