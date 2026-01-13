"""
Pytest configuration and fixtures.

Provides test database setup and common fixtures.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from core.models import (
    Policy, PolicyVersion, PolicyStatus, Signal, SignalReliability
)


# Test database URL (separate from production)
TEST_DATABASE_URL = "postgresql://govos:local_dev_password@localhost:5432/governance_os_test"


@pytest.fixture(scope="function")
def db_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Drop all tables after test
    Base.metadata.drop_all(bind=engine)
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
