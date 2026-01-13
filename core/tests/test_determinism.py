"""
Determinism Tests - CRITICAL

These tests validate the core contract of the governance kernel:
SAME INPUTS MUST PRODUCE SAME OUTPUTS EVERY TIME.

If any of these tests fail, the system is fundamentally broken.
"""

import pytest
from datetime import datetime

from core.services import Evaluator, ExceptionEngine, EvidenceGenerator
from core.domain.fingerprinting import (
    compute_evaluation_input_hash,
    compute_exception_fingerprint,
    compute_content_hash,
    normalize_signal_data
)


class TestDeterministicFingerprinting:
    """Test deterministic hashing functions."""

    def test_evaluation_hash_determinism(self, sample_policy, sample_signals):
        """
        CRITICAL: Same inputs produce same hash.

        This is the foundation of evaluation idempotency.
        """
        from uuid import UUID

        # Normalize signals
        signal_dicts = [
            {
                "id": str(s.id),
                "signal_type": s.signal_type,
                "payload": s.payload,
                "source": s.source,
                "reliability": s.reliability.value,
                "observed_at": s.observed_at.isoformat()
            }
            for s in sample_signals
        ]

        normalized = [normalize_signal_data(s) for s in signal_dicts]

        # Compute hash twice
        hash1 = compute_evaluation_input_hash(sample_policy.id, normalized)
        hash2 = compute_evaluation_input_hash(sample_policy.id, normalized)

        # MUST be identical
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex string

    def test_exception_fingerprint_determinism(self, sample_policy):
        """
        CRITICAL: Same exception parameters produce same fingerprint.

        This is the foundation of exception deduplication.
        """
        key_dimensions = {"asset": "BTC"}

        # Compute fingerprint twice
        fp1 = compute_exception_fingerprint(
            sample_policy.policy_id,
            "position_limit_breach",
            key_dimensions
        )
        fp2 = compute_exception_fingerprint(
            sample_policy.policy_id,
            "position_limit_breach",
            key_dimensions
        )

        # MUST be identical
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex string

        # Different dimensions should produce different fingerprint
        fp3 = compute_exception_fingerprint(
            sample_policy.policy_id,
            "position_limit_breach",
            {"asset": "ETH"}  # Different asset
        )
        assert fp1 != fp3

    def test_content_hash_determinism(self):
        """
        CRITICAL: Same content produces same hash.

        This is the foundation of evidence pack integrity.
        """
        content = {
            "decision": {"id": "123", "rationale": "Test"},
            "signals": [{"id": "s1"}, {"id": "s2"}]
        }

        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        # MUST be identical
        assert hash1 == hash2
        assert len(hash1) == 64


class TestEvaluatorDeterminism:
    """Test evaluator determinism - the HEART of the system."""

    def test_evaluation_determinism_basic(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Same policy + same signals = same evaluation result.

        This is THE most important test in the entire system.
        If this fails, the governance kernel is broken.
        """
        evaluator = Evaluator(db_session)

        # Run evaluation #1
        eval1 = evaluator.evaluate(sample_policy, sample_signals)

        # Clear session to simulate fresh evaluation
        db_session.expunge_all()

        # Run evaluation #2 with same inputs
        eval2 = evaluator.evaluate(sample_policy, sample_signals)

        # MUST be identical
        assert eval1.input_hash == eval2.input_hash
        assert eval1.result == eval2.result
        assert eval1.details == eval2.details

        # Should return same evaluation object (idempotency)
        assert eval1.id == eval2.id

    def test_evaluation_idempotency(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Running evaluation twice returns existing result.

        Validates idempotency: same hash → don't re-evaluate.
        """
        evaluator = Evaluator(db_session)

        # First evaluation
        eval1 = evaluator.evaluate(sample_policy, sample_signals)
        eval1_time = eval1.evaluated_at

        # Second evaluation (should return existing)
        eval2 = evaluator.evaluate(sample_policy, sample_signals)
        eval2_time = eval2.evaluated_at

        # Should be the SAME evaluation object
        assert eval1.id == eval2.id
        assert eval1_time == eval2_time  # Not re-evaluated
        assert eval1.input_hash == eval2.input_hash

    def test_evaluation_signal_order_independence(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Signal order doesn't affect evaluation.

        Evaluator must sort signals internally for determinism.
        """
        evaluator = Evaluator(db_session)

        # Evaluate with signals in order A
        eval1 = evaluator.evaluate(sample_policy, sample_signals)

        # Evaluate with signals in reverse order
        signals_reversed = list(reversed(sample_signals))
        eval2 = evaluator.evaluate(sample_policy, signals_reversed)

        # Should produce same hash (order-independent)
        assert eval1.input_hash == eval2.input_hash
        assert eval1.id == eval2.id


class TestExceptionEngineDeterminism:
    """Test exception engine determinism."""

    def test_exception_deduplication(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Duplicate exceptions are blocked.

        Same fingerprint + open status = no new exception.
        """
        from core.services import Evaluator

        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)

        # Generate evaluation
        evaluation = evaluator.evaluate(sample_policy, sample_signals)

        # Generate exception #1
        exception1 = exception_engine.generate_exception(evaluation, sample_policy)

        if exception1:
            # Try to generate same exception again
            exception2 = exception_engine.generate_exception(evaluation, sample_policy)

            # Second attempt should return None (deduped)
            assert exception2 is None


class TestEvidencePackDeterminism:
    """Test evidence pack determinism."""

    def test_evidence_pack_determinism(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Same decision produces same evidence pack.

        Evidence packs must be reproducible.
        """
        from core.services import Evaluator, ExceptionEngine, DecisionRecorder

        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)
        decision_recorder = DecisionRecorder(db_session)
        evidence_gen = EvidenceGenerator(db_session)

        # Create evaluation → exception → decision
        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            decision = decision_recorder.record_decision(
                exception_id=exception.id,
                chosen_option_id=exception.options[0]["id"],
                rationale="Test decision for determinism validation",
                decided_by="test_suite"
            )

            # Generate evidence pack twice
            pack1 = evidence_gen.generate_pack(decision)

            # Try to generate again (should return existing)
            pack2 = evidence_gen.generate_pack(decision)

            # Should be same pack
            assert pack1.id == pack2.id
            assert pack1.content_hash == pack2.content_hash
            assert pack1.evidence == pack2.evidence


class TestReplayScenarios:
    """Test replay scenarios - same inputs at different times."""

    def test_replay_with_same_timestamp(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Replay produces identical results.

        Given historical data, replay must produce same evaluations.
        """
        evaluator = Evaluator(db_session)

        # Evaluation in "production" namespace
        eval_prod = evaluator.evaluate(sample_policy, sample_signals, "production")

        # Replay in "test" namespace with same inputs
        eval_replay = evaluator.evaluate(sample_policy, sample_signals, "replay_test")

        # Input hash must be identical (deterministic)
        assert eval_prod.input_hash == eval_replay.input_hash

        # Results must be identical
        assert eval_prod.result == eval_replay.result
        assert eval_prod.details == eval_replay.details

        # But they're different evaluations (different namespace)
        assert eval_prod.id != eval_replay.id
        assert eval_prod.replay_namespace == "production"
        assert eval_replay.replay_namespace == "replay_test"


# Marker for critical tests
pytestmark = pytest.mark.critical
