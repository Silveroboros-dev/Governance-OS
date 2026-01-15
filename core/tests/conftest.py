"""
Pytest configuration and fixtures.

Provides test database setup and common fixtures.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.models import (
    Policy, PolicyVersion, PolicyStatus, Signal, SignalReliability
)
# Sprint 3 models
from core.models.approval import ApprovalQueue, ApprovalActionType, ApprovalStatus
from core.models.trace import AgentTrace, AgentType, AgentTraceStatus


# Test database URL (separate from production)
TEST_DATABASE_URL = "postgresql://govos:local_dev_password@localhost:5432/governance_os_test"


@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Drop all tables after test - handle circular dependencies with CASCADE
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a clean database session for each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()

    yield session

    session.rollback()
    session.close()


@pytest.fixture
def sample_policy(db_session):
    """Create a sample policy with active version."""
    policy = Policy(
        name="Test Position Limit Policy",
        pack="treasury",
        description="Test policy for unit tests",
        created_by="test_suite"
    )
    db_session.add(policy)
    db_session.flush()

    policy_version = PolicyVersion(
        policy_id=policy.id,
        version_number=1,
        status=PolicyStatus.ACTIVE,
        rule_definition={
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "position_limit_breach",
                    "threshold": {
                        "field": "payload.current_position",
                        "operator": ">",
                        "value": "payload.limit",
                    },
                    "severity_mapping": {
                        "duration_hours >= 2": "high",
                        "default": "medium"
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
        valid_from=datetime.utcnow() - timedelta(days=30),
        valid_to=None,
        changelog="Test version",
        created_by="test_suite"
    )
    db_session.add(policy_version)
    db_session.commit()

    return policy_version


@pytest.fixture
def sample_signals(db_session):
    """Create sample signals for testing."""
    signals = []

    # Signal 1: BTC position breach
    signal1 = Signal(
        pack="treasury",
        signal_type="position_limit_breach",
        payload={
            "asset": "BTC",
            "current_position": 120,
            "limit": 100,
            "duration_hours": 2
        },
        source="test_system",
        reliability=SignalReliability.HIGH,
        observed_at=datetime.utcnow() - timedelta(hours=2),
        signal_metadata={"test": True}
    )
    signals.append(signal1)

    # Signal 2: ETH position breach (lower severity)
    signal2 = Signal(
        pack="treasury",
        signal_type="position_limit_breach",
        payload={
            "asset": "ETH",
            "current_position": 55,
            "limit": 50,
            "duration_hours": 0.5
        },
        source="test_system",
        reliability=SignalReliability.HIGH,
        observed_at=datetime.utcnow() - timedelta(minutes=30),
        signal_metadata={"test": True}
    )
    signals.append(signal2)

    db_session.add_all(signals)
    db_session.commit()

    return signals


# Sprint 3 fixtures

@pytest.fixture
def sample_trace(db_session):
    """Create a sample agent trace."""
    trace = AgentTrace(
        agent_type=AgentType.INTAKE,
        session_id=uuid4(),
        pack="treasury",
        document_source="email/inbox/test_123",
        input_summary={"document_length": 5000, "source": "email"},
    )
    db_session.add(trace)
    db_session.commit()
    return trace


@pytest.fixture
def sample_approval(db_session, sample_trace):
    """Create a sample approval queue entry."""
    approval = ApprovalQueue(
        action_type=ApprovalActionType.SIGNAL,
        payload={
            "pack": "treasury",
            "signal_type": "position_limit_breach",
            "payload": {"asset": "BTC", "position": 120, "limit": 100},
            "source": "email/inbox/test_123",
        },
        proposed_by="intake_agent",
        summary="Position limit breach for BTC",
        confidence=0.85,
        trace_id=sample_trace.id,
    )
    db_session.add(approval)
    db_session.commit()
    return approval


@pytest.fixture
def multiple_approvals(db_session):
    """Create multiple approval queue entries with different statuses."""
    approvals = []

    # Pending signal approval
    approvals.append(ApprovalQueue(
        action_type=ApprovalActionType.SIGNAL,
        payload={"pack": "treasury", "signal_type": "type_1"},
        proposed_by="intake_agent",
        status=ApprovalStatus.PENDING,
    ))

    # Approved policy draft
    approved = ApprovalQueue(
        action_type=ApprovalActionType.POLICY_DRAFT,
        payload={"pack": "treasury", "name": "Test Policy"},
        proposed_by="policy_draft_agent",
        status=ApprovalStatus.APPROVED,
        reviewed_by="test_user",
        reviewed_at=datetime.utcnow(),
    )
    approvals.append(approved)

    # Rejected dismiss request
    rejected = ApprovalQueue(
        action_type=ApprovalActionType.DISMISS,
        payload={"exception_id": str(uuid4())},
        proposed_by="agent",
        status=ApprovalStatus.REJECTED,
        reviewed_by="test_user",
        reviewed_at=datetime.utcnow(),
        review_notes="Not appropriate to dismiss",
    )
    approvals.append(rejected)

    db_session.add_all(approvals)
    db_session.commit()
    return approvals


@pytest.fixture
def multiple_traces(db_session):
    """Create multiple agent traces with different statuses."""
    traces = []

    # Running intake trace
    traces.append(AgentTrace(
        agent_type=AgentType.INTAKE,
        session_id=uuid4(),
        status=AgentTraceStatus.RUNNING,
        pack="treasury",
    ))

    # Completed narrative trace
    completed = AgentTrace(
        agent_type=AgentType.NARRATIVE,
        session_id=uuid4(),
        status=AgentTraceStatus.COMPLETED,
        completed_at=datetime.utcnow(),
        total_duration_ms=1500,
    )
    traces.append(completed)

    # Failed policy draft trace
    failed = AgentTrace(
        agent_type=AgentType.POLICY_DRAFT,
        session_id=uuid4(),
        status=AgentTraceStatus.FAILED,
        completed_at=datetime.utcnow(),
        error_message="LLM rate limit exceeded",
    )
    traces.append(failed)

    db_session.add_all(traces)
    db_session.commit()
    return traces
