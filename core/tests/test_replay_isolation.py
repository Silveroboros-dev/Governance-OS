"""
Tests for replay isolation.

Verifies that replay operations do NOT mutate production data.
This is a critical requirement per CLAUDE.md architecture principles.
"""

import pytest
from datetime import datetime, timedelta

from core.services.evaluator import Evaluator
from core.services.exception_engine import ExceptionEngine
from core.models import Evaluation, Exception as DBException, AuditEvent


class TestReplayIsolation:
    """Test that replay mode does not affect production data."""

    def test_evaluator_dry_run_does_not_persist(self, db_session, sample_policy, sample_signals):
        """Evaluator with dry_run=True should not write to database."""
        evaluator = Evaluator(db_session)

        # Count existing records
        eval_count_before = db_session.query(Evaluation).count()
        audit_count_before = db_session.query(AuditEvent).count()

        # Run evaluation in dry_run mode
        evaluation = evaluator.evaluate(
            sample_policy,
            sample_signals,
            replay_namespace="replay:test",
            dry_run=True
        )

        # Verify evaluation was created (in-memory)
        assert evaluation is not None
        assert evaluation.result is not None
        assert evaluation.input_hash is not None

        # Verify NO database writes occurred
        eval_count_after = db_session.query(Evaluation).count()
        audit_count_after = db_session.query(AuditEvent).count()

        assert eval_count_after == eval_count_before, "dry_run should not persist Evaluation records"
        assert audit_count_after == audit_count_before, "dry_run should not persist AuditEvent records"

    def test_evaluator_normal_mode_does_persist(self, db_session, sample_policy, sample_signals):
        """Evaluator without dry_run should write to database (control test)."""
        evaluator = Evaluator(db_session)

        # Count existing records
        eval_count_before = db_session.query(Evaluation).count()

        # Run evaluation in normal mode
        evaluation = evaluator.evaluate(
            sample_policy,
            sample_signals,
            replay_namespace="production"
        )

        # Verify database write occurred
        eval_count_after = db_session.query(Evaluation).count()

        assert eval_count_after == eval_count_before + 1, "Normal mode should persist Evaluation"
        assert evaluation.id is not None, "Evaluation should have ID after persistence"

    def test_exception_engine_dry_run_does_not_persist(self, db_session, sample_policy, sample_signals):
        """ExceptionEngine with dry_run=True should not write to database."""
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)

        # First create an evaluation that will fail (trigger exception)
        # We need a policy that will produce a FAIL result
        evaluation = evaluator.evaluate(
            sample_policy,
            sample_signals,
            dry_run=True
        )

        # Count existing exception records
        exception_count_before = db_session.query(DBException).count()
        audit_count_before = db_session.query(AuditEvent).count()

        # Generate exception in dry_run mode
        exception = exception_engine.generate_exception(
            evaluation,
            sample_policy,
            dry_run=True
        )

        # Exception may be None if evaluation passed - that's OK
        # But if it's not None, it should NOT be persisted
        exception_count_after = db_session.query(DBException).count()
        audit_count_after = db_session.query(AuditEvent).count()

        assert exception_count_after == exception_count_before, "dry_run should not persist Exception records"
        assert audit_count_after == audit_count_before, "dry_run should not persist AuditEvent records"

    def test_replay_namespace_is_isolated(self, db_session, sample_policy, sample_signals):
        """Different replay namespaces should be isolated from production."""
        evaluator = Evaluator(db_session)

        # Run evaluation in production namespace
        prod_evaluation = evaluator.evaluate(
            sample_policy,
            [sample_signals[0]],  # Use just first signal
            replay_namespace="production"
        )

        # Run same evaluation in replay namespace
        replay_evaluation = evaluator.evaluate(
            sample_policy,
            [sample_signals[0]],
            replay_namespace="replay:test-123"
        )

        # Both should succeed
        assert prod_evaluation is not None
        assert replay_evaluation is not None

        # They should have the same input_hash (same inputs)
        assert prod_evaluation.input_hash == replay_evaluation.input_hash

        # But they should be different records (different namespaces)
        assert prod_evaluation.id != replay_evaluation.id
        assert prod_evaluation.replay_namespace == "production"
        assert replay_evaluation.replay_namespace == "replay:test-123"

        # Query should be able to filter by namespace
        prod_only = db_session.query(Evaluation).filter(
            Evaluation.replay_namespace == "production"
        ).all()
        replay_only = db_session.query(Evaluation).filter(
            Evaluation.replay_namespace.like("replay:%")
        ).all()

        assert len(prod_only) >= 1
        assert len(replay_only) >= 1
        assert prod_evaluation.id in [e.id for e in prod_only]
        assert replay_evaluation.id in [e.id for e in replay_only]
