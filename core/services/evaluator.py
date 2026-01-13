"""
Evaluator Service.

The deterministic evaluation engine.
This is the HEART of the governance kernel.

CRITICAL: This service must be deterministic.
Same inputs MUST produce same outputs EVERY TIME.
"""

from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.models import Evaluation, PolicyVersion, Signal, EvaluationResult, AuditEvent, AuditEventType
from core.domain.fingerprinting import compute_evaluation_input_hash, normalize_signal_data
from core.domain.evaluation_rules import evaluate_policy


class Evaluator:
    """
    Deterministic policy evaluation engine.

    Executes policy rules against signals and produces structured evaluation results.
    Guarantees determinism via input hashing and idempotency checks.
    """

    def __init__(self, db: Session):
        """
        Initialize evaluator.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def evaluate(
        self,
        policy_version: PolicyVersion,
        signals: List[Signal],
        replay_namespace: str = "production"
    ) -> Evaluation:
        """
        Execute deterministic policy evaluation.

        CRITICAL GUARANTEES:
        1. Same policy + same signals → same result (determinism)
        2. Same input_hash → return existing evaluation (idempotency)
        3. Signal order doesn't matter (signals are sorted internally)

        Args:
            policy_version: PolicyVersion to evaluate
            signals: List of Signal objects
            replay_namespace: Namespace for replay scenarios (default: "production")

        Returns:
            Evaluation object

        Example:
            >>> evaluator = Evaluator(db)
            >>> evaluation = evaluator.evaluate(policy, signals)
            >>> evaluation.result
            'fail'
            >>> evaluation.input_hash
            'a1b2c3d4...'
        """
        # Step 1: Normalize and sort signals for determinism
        signal_dicts = [self._signal_to_dict(s) for s in signals]
        signal_dicts_sorted = sorted(signal_dicts, key=lambda s: s["id"])

        # Step 2: Compute input hash
        normalized_signals = [normalize_signal_data(s) for s in signal_dicts_sorted]
        input_hash = compute_evaluation_input_hash(
            policy_version.id,
            normalized_signals
        )

        # Step 3: Check for existing evaluation (idempotency)
        existing = (
            self.db.query(Evaluation)
            .filter(
                Evaluation.input_hash == input_hash,
                Evaluation.replay_namespace == replay_namespace
            )
            .first()
        )

        if existing:
            # Already evaluated - return existing result
            return existing

        # Step 4: Execute policy rules
        result_str, details = evaluate_policy(
            policy_version.rule_definition,
            signal_dicts_sorted
        )

        # Map string result to enum
        result_enum = self._map_result(result_str)

        # Step 5: Create evaluation record
        evaluation = Evaluation(
            policy_version_id=policy_version.id,
            signal_ids=[s.id for s in signals],
            result=result_enum,
            details=details,
            input_hash=input_hash,
            replay_namespace=replay_namespace
        )

        self.db.add(evaluation)
        self.db.flush()  # Get evaluation ID

        # Step 6: Create audit event
        audit_event = AuditEvent(
            event_type=AuditEventType.EVALUATION_EXECUTED,
            aggregate_type="evaluation",
            aggregate_id=evaluation.id,
            event_data={
                "policy_version_id": str(policy_version.id),
                "signal_count": len(signals),
                "result": result_str,
                "input_hash": input_hash
            },
            actor="system",
            replay_namespace=replay_namespace
        )

        self.db.add(audit_event)
        self.db.commit()

        return evaluation

    def _signal_to_dict(self, signal: Signal) -> Dict[str, Any]:
        """
        Convert Signal ORM object to dictionary.

        Args:
            signal: Signal object

        Returns:
            Dictionary representation
        """
        return {
            "id": signal.id,
            "signal_type": signal.signal_type,
            "payload": signal.payload,
            "source": signal.source,
            "reliability": signal.reliability.value if hasattr(signal.reliability, 'value') else signal.reliability,
            "observed_at": signal.observed_at,
            "metadata": signal.signal_metadata
        }

    def _map_result(self, result_str: str) -> EvaluationResult:
        """
        Map string result to EvaluationResult enum.

        Args:
            result_str: "pass" | "fail" | "inconclusive"

        Returns:
            EvaluationResult enum value
        """
        mapping = {
            "pass": EvaluationResult.PASS,
            "fail": EvaluationResult.FAIL,
            "inconclusive": EvaluationResult.INCONCLUSIVE
        }
        return mapping.get(result_str, EvaluationResult.INCONCLUSIVE)

    def _compute_input_hash(
        self,
        policy_version_id: UUID,
        signals: List[Signal]
    ) -> str:
        """
        Compute deterministic hash for evaluation inputs.

        This is a wrapper around the domain function that works with ORM objects.

        Args:
            policy_version_id: UUID of policy version
            signals: List of Signal objects (will be sorted internally)

        Returns:
            SHA256 hash (64-character hex string)
        """
        signal_dicts = [self._signal_to_dict(s) for s in signals]
        signal_dicts_sorted = sorted(signal_dicts, key=lambda s: str(s["id"]))
        normalized = [normalize_signal_data(s) for s in signal_dicts_sorted]

        return compute_evaluation_input_hash(policy_version_id, normalized)
