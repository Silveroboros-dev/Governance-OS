"""
Service Layer Tests.

Tests for individual service components.
"""

import pytest
from datetime import datetime, timedelta

from core.services import (
    PolicyEngine, Evaluator, ExceptionEngine,
    DecisionRecorder, EvidenceGenerator
)
from core.models import ExceptionStatus, EvaluationResult


class TestPolicyEngine:
    """Test policy engine service."""

    def test_get_active_policies(self, db_session, sample_policy):
        """Test retrieving active policies for a pack."""
        engine = PolicyEngine(db_session)

        policies = engine.get_active_policies("treasury")

        assert len(policies) == 1
        assert policies[0].id == sample_policy.id
        assert policies[0].policy.pack == "treasury"

    def test_get_active_policies_empty_pack(self, db_session):
        """Test retrieving policies for non-existent pack."""
        engine = PolicyEngine(db_session)

        policies = engine.get_active_policies("nonexistent")

        assert len(policies) == 0


class TestEvaluator:
    """Test evaluator service."""

    def test_evaluate_basic(self, db_session, sample_policy, sample_signals):
        """Test basic evaluation."""
        evaluator = Evaluator(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)

        assert evaluation is not None
        assert evaluation.policy_version_id == sample_policy.id
        assert len(evaluation.signal_ids) == len(sample_signals)
        assert evaluation.input_hash is not None
        assert len(evaluation.input_hash) == 64  # SHA256

    def test_evaluate_creates_audit_event(self, db_session, sample_policy, sample_signals):
        """Test that evaluation creates audit event."""
        from core.models import AuditEvent, AuditEventType

        evaluator = Evaluator(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)

        # Check audit event was created
        audit_event = (
            db_session.query(AuditEvent)
            .filter(
                AuditEvent.aggregate_id == evaluation.id,
                AuditEvent.event_type == AuditEventType.EVALUATION_EXECUTED
            )
            .first()
        )

        assert audit_event is not None
        assert audit_event.aggregate_type == "evaluation"


class TestExceptionEngine:
    """Test exception engine service."""

    def test_generate_exception_for_failed_evaluation(self, db_session, sample_policy, sample_signals):
        """Test exception generation for failed evaluation."""
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)

        # Generate exception
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if evaluation.result == EvaluationResult.FAIL:
            assert exception is not None
            assert exception.evaluation_id == evaluation.id
            assert exception.status == ExceptionStatus.OPEN
            assert len(exception.options) >= 2  # At least 2 options
            assert exception.fingerprint is not None

            # Verify options are symmetric (no "recommended" field)
            for option in exception.options:
                assert "recommended" not in option
                assert "id" in option
                assert "label" in option
                assert "description" in option

    def test_exception_options_are_symmetric(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Exception options must be symmetric.

        No "recommended" or "popular" or "default" fields allowed.
        """
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            for option in exception.options:
                # Verify no ranking/recommendation fields
                forbidden_fields = ["recommended", "default", "popular", "priority", "weight", "ranking"]
                for field in forbidden_fields:
                    assert field not in option, f"Option should not have '{field}' field"


class TestDecisionRecorder:
    """Test decision recorder service."""

    def test_record_decision_basic(self, db_session, sample_policy, sample_signals):
        """Test basic decision recording."""
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)
        decision_recorder = DecisionRecorder(db_session)

        # Create exception
        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            # Record decision
            decision = decision_recorder.record_decision(
                exception_id=exception.id,
                chosen_option_id=exception.options[0]["id"],
                rationale="Test rationale for decision validation",
                decided_by="test_suite"
            )

            assert decision is not None
            assert decision.exception_id == exception.id
            assert decision.rationale == "Test rationale for decision validation"
            assert decision.decided_by == "test_suite"

            # Exception should be resolved
            db_session.refresh(exception)
            assert exception.status == ExceptionStatus.RESOLVED

    def test_record_decision_requires_rationale(self, db_session, sample_policy, sample_signals):
        """Test that rationale is required."""
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)
        decision_recorder = DecisionRecorder(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            # Try to record decision without rationale
            with pytest.raises(ValueError, match="(?i)rationale"):
                decision_recorder.record_decision(
                    exception_id=exception.id,
                    chosen_option_id=exception.options[0]["id"],
                    rationale="",  # Empty!
                    decided_by="test_suite"
                )

    def test_record_decision_validates_option(self, db_session, sample_policy, sample_signals):
        """Test that chosen option must be valid."""
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)
        decision_recorder = DecisionRecorder(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            # Try to record decision with invalid option
            with pytest.raises(ValueError, match="Invalid option"):
                decision_recorder.record_decision(
                    exception_id=exception.id,
                    chosen_option_id="nonexistent_option",  # Invalid!
                    rationale="Test rationale",
                    decided_by="test_suite"
                )

    def test_hard_override_requires_approval(self, db_session, sample_policy, sample_signals):
        """
        CRITICAL: Hard overrides MUST have approved_by.

        This is a governance enforcement requirement (#28).
        """
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)
        decision_recorder = DecisionRecorder(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            # Try to record hard override without approval
            with pytest.raises(ValueError, match="(?i)approved_by|approval"):
                decision_recorder.record_decision(
                    exception_id=exception.id,
                    chosen_option_id=exception.options[0]["id"],
                    rationale="Override rationale",
                    decided_by="test_suite",
                    is_hard_override=True,  # Hard override!
                    approved_by=None  # Missing approval!
                )

    def test_hard_override_with_approval_succeeds(self, db_session, sample_policy, sample_signals):
        """
        Hard override with proper approval should succeed.

        Validates full hard override flow (#28).
        """
        from core.models import DecisionType

        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)
        decision_recorder = DecisionRecorder(db_session)

        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            # Record hard override with approval
            decision = decision_recorder.record_decision(
                exception_id=exception.id,
                chosen_option_id=exception.options[0]["id"],
                rationale="Override rationale with proper justification",
                decided_by="decider_user",
                is_hard_override=True,
                approved_by="approver_user",
                approval_notes="Approved due to exceptional circumstances"
            )

            assert decision is not None
            assert decision.is_hard_override is True
            assert decision.decision_type == DecisionType.HARD_OVERRIDE
            assert decision.approved_by == "approver_user"
            assert decision.approved_at is not None
            assert decision.approval_notes == "Approved due to exceptional circumstances"


class TestEvidenceGenerator:
    """Test evidence generator service."""

    def test_generate_evidence_pack(self, db_session, sample_policy, sample_signals):
        """Test evidence pack generation."""
        evaluator = Evaluator(db_session)
        exception_engine = ExceptionEngine(db_session)
        decision_recorder = DecisionRecorder(db_session)
        evidence_gen = EvidenceGenerator(db_session)

        # Create full chain
        evaluation = evaluator.evaluate(sample_policy, sample_signals)
        exception = exception_engine.generate_exception(evaluation, sample_policy)

        if exception:
            decision = decision_recorder.record_decision(
                exception_id=exception.id,
                chosen_option_id=exception.options[0]["id"],
                rationale="Test rationale for evidence pack validation",
                decided_by="test_suite"
            )

            # Generate evidence pack
            pack = evidence_gen.generate_pack(decision)

            assert pack is not None
            assert pack.decision_id == decision.id
            assert pack.content_hash is not None
            assert len(pack.content_hash) == 64  # SHA256

            # Verify evidence structure
            evidence = pack.evidence
            assert "decision" in evidence
            assert "exception" in evidence
            assert "evaluation" in evidence
            assert "policy" in evidence
            assert "signals" in evidence
            assert "audit_trail" in evidence

            # Verify completeness
            assert evidence["decision"]["rationale"] == decision.rationale
            assert evidence["exception"]["title"] == exception.title
            assert len(evidence["signals"]) == len(sample_signals)
