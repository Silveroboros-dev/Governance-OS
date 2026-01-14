"""
Shared pytest fixtures for Sprint 2 tests.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


# ============================================================================
# SIGNAL FIXTURES
# ============================================================================

@pytest.fixture
def sample_signal_data() -> Dict[str, Any]:
    """Sample signal data for testing."""
    return {
        "signal_type": "position_limit_breach",
        "source": "test_system",
        "payload": {
            "asset": "BTC",
            "current_position": 150000000,
            "limit": 100000000,
            "currency": "USD",
        },
        "timestamp": datetime.utcnow(),
        "reliability": 0.95,
    }


@pytest.fixture
def sample_signals() -> List[Dict[str, Any]]:
    """Multiple sample signals for testing."""
    return [
        {
            "signal_type": "position_limit_breach",
            "source": "position_monitor",
            "payload": {
                "asset": "BTC",
                "current_position": 150000000,
                "limit": 100000000,
            },
            "timestamp": datetime(2025, 1, 15, 10, 0, 0),
        },
        {
            "signal_type": "market_volatility_spike",
            "source": "volatility_monitor",
            "payload": {
                "asset": "ETH",
                "volatility": 0.85,
                "threshold": 0.6,
            },
            "timestamp": datetime(2025, 1, 15, 11, 0, 0),
        },
        {
            "signal_type": "counterparty_credit_downgrade",
            "source": "credit_system",
            "payload": {
                "counterparty": "Bank A",
                "old_rating": "A",
                "new_rating": "BBB",
                "exposure_usd": 5000000,
            },
            "timestamp": datetime(2025, 1, 15, 12, 0, 0),
        },
    ]


# ============================================================================
# POLICY FIXTURES
# ============================================================================

@pytest.fixture
def sample_policy() -> Dict[str, Any]:
    """Sample policy for testing."""
    return {
        "id": "policy-001",
        "name": "Position Limit Policy",
        "current_version": {
            "id": "version-001",
            "rule_definition": {
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
                            "default": "high",
                        },
                    }
                ],
                "evaluation_logic": "any_condition_met",
            },
        },
    }


@pytest.fixture
def sample_policies() -> List[Dict[str, Any]]:
    """Multiple sample policies for testing."""
    return [
        {
            "id": "policy-001",
            "name": "Position Limit Policy",
            "current_version": {
                "id": "version-001",
                "rule_definition": {
                    "type": "threshold_breach",
                    "conditions": [
                        {
                            "signal_type": "position_limit_breach",
                            "threshold": {
                                "field": "payload.current_position",
                                "operator": ">",
                                "value": "payload.limit",
                            },
                            "severity_mapping": {"default": "high"},
                        }
                    ],
                    "evaluation_logic": "any_condition_met",
                },
            },
        },
        {
            "id": "policy-002",
            "name": "Volatility Policy",
            "current_version": {
                "id": "version-002",
                "rule_definition": {
                    "type": "threshold_breach",
                    "conditions": [
                        {
                            "signal_type": "market_volatility_spike",
                            "threshold": {
                                "field": "payload.volatility",
                                "operator": ">",
                                "value": "payload.threshold",
                            },
                            "severity_mapping": {"default": "medium"},
                        }
                    ],
                    "evaluation_logic": "any_condition_met",
                },
            },
        },
    ]


# ============================================================================
# EVIDENCE PACK FIXTURES
# ============================================================================

@pytest.fixture
def sample_evidence_pack() -> Dict[str, Any]:
    """Sample evidence pack for testing."""
    return {
        "evidence_pack_id": "evp_test_001",
        "generated_at": datetime.utcnow().isoformat(),
        "decision": {
            "id": "dec_001",
            "decided_at": datetime.utcnow().isoformat(),
            "decided_by": "user@example.com",
            "rationale": "Position exceeded limit, immediate reduction required",
            "assumptions": "Market conditions stable",
        },
        "evidence_items": [
            {
                "evidence_id": "sig_001",
                "type": "signal",
                "data": {
                    "signal_type": "position_limit_breach",
                    "source": "position_monitor",
                    "payload": {
                        "asset": "BTC",
                        "current_position": 150000000,
                        "limit": 100000000,
                    },
                },
            },
            {
                "evidence_id": "exc_001",
                "type": "exception_context",
                "data": {
                    "asset": "BTC",
                    "breach_amount": 50000000,
                },
            },
            {
                "evidence_id": "eval_001",
                "type": "evaluation",
                "data": {
                    "result": "fail",
                    "severity": "high",
                },
            },
            {
                "evidence_id": "opt_001",
                "type": "chosen_option",
                "data": {
                    "label": "Reduce Position Immediately",
                    "description": "Sell excess position to return within limits",
                },
            },
            {
                "evidence_id": "pol_001",
                "type": "policy",
                "data": {
                    "name": "Position Limit Policy",
                    "rule_definition": {"type": "threshold_breach"},
                },
            },
        ],
    }


# ============================================================================
# MEMO FIXTURES
# ============================================================================

@pytest.fixture
def sample_grounded_memo_data() -> Dict[str, Any]:
    """Sample properly grounded memo data."""
    return {
        "decision_id": "dec_001",
        "title": "Position Limit Breach Resolution",
        "sections": [
            {
                "heading": "Situation",
                "claims": [
                    {
                        "text": "BTC position reached $150M, exceeding the $100M limit",
                        "evidence_refs": [
                            {"evidence_id": "sig_001", "evidence_type": "signal"}
                        ],
                    },
                    {
                        "text": "The breach triggered a high-severity exception",
                        "evidence_refs": [
                            {"evidence_id": "exc_001", "evidence_type": "exception_context"},
                            {"evidence_id": "eval_001", "evidence_type": "evaluation"},
                        ],
                    },
                ],
            },
            {
                "heading": "Decision",
                "claims": [
                    {
                        "text": "The decision was made to reduce position immediately",
                        "evidence_refs": [
                            {"evidence_id": "opt_001", "evidence_type": "chosen_option"}
                        ],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def sample_ungrounded_memo_data() -> Dict[str, Any]:
    """Sample memo with ungrounded claims."""
    return {
        "decision_id": "dec_002",
        "title": "Ungrounded Memo",
        "sections": [
            {
                "heading": "Analysis",
                "claims": [
                    {
                        "text": "This claim has no evidence references",
                        "evidence_refs": [],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def sample_memo_with_recommendations() -> Dict[str, Any]:
    """Sample memo containing forbidden recommendation language."""
    return {
        "decision_id": "dec_003",
        "title": "Memo With Recommendations",
        "sections": [
            {
                "heading": "Suggestion",
                "claims": [
                    {
                        "text": "The team should consider reducing exposure more aggressively",
                        "evidence_refs": [
                            {"evidence_id": "sig_001", "evidence_type": "signal"}
                        ],
                    },
                ],
            },
        ],
    }


# ============================================================================
# CSV FIXTURES
# ============================================================================

@pytest.fixture
def sample_csv_content() -> str:
    """Sample CSV content for ingestion testing."""
    return """signal_type,timestamp,source,asset,current_position,limit
position_limit_breach,2025-01-15 10:00:00,test_system,BTC,150000000,100000000
position_limit_breach,2025-01-15 11:00:00,test_system,ETH,80000000,50000000
market_volatility_spike,2025-01-15 12:00:00,volatility_monitor,BTC,0.85,0.6
"""


@pytest.fixture
def sample_csv_file(tmp_path, sample_csv_content) -> Path:
    """Create a temporary CSV file for testing."""
    csv_path = tmp_path / "test_signals.csv"
    csv_path.write_text(sample_csv_content)
    return csv_path


# ============================================================================
# REPLAY FIXTURES
# ============================================================================

@pytest.fixture
def replay_config():
    """Sample replay configuration."""
    from replay.harness import ReplayConfig
    return ReplayConfig(
        namespace="test_replay",
        pack="treasury",
        from_date=datetime(2025, 1, 1),
        to_date=datetime(2025, 3, 31),
    )
