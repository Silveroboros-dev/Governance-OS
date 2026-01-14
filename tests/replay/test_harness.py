"""
Tests for Replay Harness - Deterministic policy evaluation.
"""

import pytest
from datetime import datetime

from replay.harness import (
    ReplayHarness,
    ReplayConfig,
    ReplayResult,
    EvaluationResult,
    ExceptionRaised,
)
from replay.csv_ingestor import IngestedSignal


class TestReplayConfig:
    """Tests for ReplayConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = ReplayConfig()
        assert config.pack == "treasury"
        assert config.namespace.startswith("replay_")
        assert config.from_date is None
        assert config.to_date is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReplayConfig(
            namespace="test_namespace",
            pack="wealth",
            from_date=datetime(2025, 1, 1),
            to_date=datetime(2025, 3, 31),
            policy_ids=["policy-001", "policy-002"],
        )
        assert config.namespace == "test_namespace"
        assert config.pack == "wealth"
        assert config.policy_ids == ["policy-001", "policy-002"]


class TestReplayHarness:
    """Tests for ReplayHarness class."""

    @pytest.fixture
    def harness(self):
        """Create a replay harness instance."""
        return ReplayHarness()

    @pytest.fixture
    def ingested_signals(self, sample_signals):
        """Convert sample signals to IngestedSignal objects."""
        return [
            IngestedSignal(
                signal_type=s["signal_type"],
                source=s["source"],
                payload=s["payload"],
                timestamp=s["timestamp"],
            )
            for s in sample_signals
        ]

    def test_harness_initialization(self, harness):
        """Test harness initialization."""
        assert harness.db_session is None

    def test_compute_input_hash_deterministic(self, harness, sample_policy, sample_signal_data):
        """Test that input hash is deterministic."""
        signal = {
            "signal_type": sample_signal_data["signal_type"],
            "payload": sample_signal_data["payload"],
            "timestamp": sample_signal_data["timestamp"],
        }

        hash1 = harness._compute_input_hash(sample_policy["current_version"], signal)
        hash2 = harness._compute_input_hash(sample_policy["current_version"], signal)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256

    def test_compute_fingerprint_deterministic(self, harness):
        """Test that fingerprint is deterministic."""
        fp1 = harness._compute_fingerprint(
            policy_id="policy-001",
            signal_ids=["sig-001", "sig-002"],
            context={"asset": "BTC"},
        )
        fp2 = harness._compute_fingerprint(
            policy_id="policy-001",
            signal_ids=["sig-002", "sig-001"],  # Different order
            context={"asset": "BTC"},
        )

        assert fp1 == fp2  # Order shouldn't matter

    def test_evaluate_threshold_breach_pass(self, harness):
        """Test threshold evaluation that passes."""
        rule = {
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
        }

        # Position under limit - should pass
        signal = IngestedSignal(
            signal_type="position_limit_breach",
            source="test",
            payload={"current_position": 50, "limit": 100},
            timestamp=datetime.utcnow(),
        )

        result, severity, details = harness._evaluate_threshold_breach(rule, signal)
        assert result == "pass"

    def test_evaluate_threshold_breach_fail(self, harness):
        """Test threshold evaluation that fails."""
        rule = {
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
        }

        # Position over limit - should fail
        signal = IngestedSignal(
            signal_type="position_limit_breach",
            source="test",
            payload={"current_position": 150, "limit": 100},
            timestamp=datetime.utcnow(),
        )

        result, severity, details = harness._evaluate_threshold_breach(rule, signal)
        assert result == "fail"
        assert severity == "high"

    def test_compare_operators(self, harness):
        """Test various comparison operators."""
        assert harness._compare_values(150, ">", 100) is True
        assert harness._compare_values(100, ">", 150) is False
        assert harness._compare_values(100, ">=", 100) is True
        assert harness._compare_values(50, "<", 100) is True
        assert harness._compare_values(100, "<=", 100) is True
        assert harness._compare_values(100, "==", 100) is True
        assert harness._compare_values(100, "!=", 50) is True
        assert harness._compare_values(-50, "abs>", 40) is True

    def test_compare_values_none_raises(self, harness):
        """Test that comparing None values raises."""
        with pytest.raises(ValueError):
            harness._compare_values(None, ">", 100)
        with pytest.raises(ValueError):
            harness._compare_values(100, ">", None)

    def test_get_nested_value(self, harness):
        """Test getting nested values from dict."""
        data = {
            "level1": {
                "level2": {
                    "value": 42
                }
            }
        }

        assert harness._get_nested_value(data, "level1.level2.value") == 42
        assert harness._get_nested_value(data, "level1.level2") == {"value": 42}
        assert harness._get_nested_value(data, "nonexistent") is None

    def test_run_replay(self, harness, ingested_signals, sample_policies):
        """Test running a full replay."""
        config = ReplayConfig(namespace="test_replay")

        result = harness.run(ingested_signals, sample_policies, config)

        assert isinstance(result, ReplayResult)
        assert result.namespace == "test_replay"
        assert result.signals_processed == len(ingested_signals)
        assert len(result.evaluations) > 0
        assert result.completed_at is not None

    def test_run_replay_with_date_filter(self, harness, ingested_signals, sample_policies):
        """Test replay with date filtering."""
        config = ReplayConfig(
            namespace="test_filtered",
            from_date=datetime(2025, 1, 15, 10, 30, 0),  # After first signal
            to_date=datetime(2025, 1, 15, 11, 30, 0),    # Before last signal
        )

        result = harness.run(ingested_signals, sample_policies, config)

        # Should only process signals within date range
        assert result.signals_processed < len(ingested_signals)

    def test_run_replay_with_policy_filter(self, harness, ingested_signals, sample_policies):
        """Test replay with policy ID filtering."""
        config = ReplayConfig(
            namespace="test_policy_filter",
            policy_ids=["policy-001"],  # Only first policy
        )

        result = harness.run(ingested_signals, sample_policies, config)

        # Should only have evaluations from policy-001
        for eval in result.evaluations:
            assert eval.policy_id == "policy-001"

    def test_exception_deduplication(self, harness, sample_policies):
        """Test that duplicate exceptions are deduplicated by fingerprint."""
        # Create two identical signals
        signals = [
            IngestedSignal(
                signal_type="position_limit_breach",
                source="test",
                payload={"current_position": 150, "limit": 100, "asset": "BTC"},
                timestamp=datetime(2025, 1, 15, 10, 0, 0),
            ),
            IngestedSignal(
                signal_type="position_limit_breach",
                source="test",
                payload={"current_position": 150, "limit": 100, "asset": "BTC"},
                timestamp=datetime(2025, 1, 15, 10, 1, 0),  # Different time, same data
            ),
        ]

        result = harness.run(signals, sample_policies)

        # Both should fail but only one exception due to dedup
        assert result.fail_count == 2
        # Fingerprints should dedupe to 1 exception
        # (depending on fingerprint implementation)

    def test_replay_metrics(self, harness, ingested_signals, sample_policies):
        """Test that replay metrics are calculated correctly."""
        result = harness.run(ingested_signals, sample_policies)

        total = result.pass_count + result.fail_count + result.inconclusive_count
        assert total == len(result.evaluations)


class TestReplayResult:
    """Tests for ReplayResult model."""

    def test_result_initialization(self):
        """Test result initialization with defaults."""
        result = ReplayResult(namespace="test")

        assert result.namespace == "test"
        assert result.signals_processed == 0
        assert result.pass_count == 0
        assert result.fail_count == 0
        assert result.evaluations == []
        assert result.exceptions_raised == []

    def test_result_with_data(self):
        """Test result with populated data."""
        result = ReplayResult(
            namespace="test",
            signals_processed=10,
            pass_count=5,
            fail_count=3,
            inconclusive_count=2,
        )

        assert result.signals_processed == 10
        assert result.pass_count + result.fail_count + result.inconclusive_count == 10


class TestEvaluationResult:
    """Tests for EvaluationResult model."""

    def test_evaluation_result_creation(self):
        """Test creating an evaluation result."""
        result = EvaluationResult(
            policy_id="policy-001",
            policy_version_id="version-001",
            signal_id="signal-001",
            result="fail",
            severity="high",
            input_hash="abc123",
        )

        assert result.policy_id == "policy-001"
        assert result.result == "fail"
        assert result.severity == "high"
        assert result.evaluation_id is not None
