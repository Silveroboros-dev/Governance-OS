"""
Replay Harness - Deterministic policy evaluation for historical data.

Executes policy evaluations in an isolated namespace without affecting
production data. Enables policy tuning and what-if analysis.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .csv_ingestor import IngestedSignal


class ReplayConfig(BaseModel):
    """Configuration for a replay run."""

    namespace: str = Field(default_factory=lambda: f"replay_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    pack: str = "treasury"
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    policy_ids: Optional[List[str]] = None  # If None, use all active policies


class EvaluationResult(BaseModel):
    """Result of a single policy evaluation."""

    evaluation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    policy_id: str
    policy_version_id: str
    signal_id: str
    result: str  # pass, fail, inconclusive
    severity: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class ExceptionRaised(BaseModel):
    """Exception raised during replay."""

    exception_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    severity: str
    policy_id: str
    evaluation_id: str
    signal_ids: List[str]
    context: Dict[str, Any]
    fingerprint: str


class ReplayResult(BaseModel):
    """Complete result of a replay run."""

    replay_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    namespace: str
    config: Optional[ReplayConfig] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Results
    signals_processed: int = 0
    evaluations: List[EvaluationResult] = Field(default_factory=list)
    exceptions_raised: List[ExceptionRaised] = Field(default_factory=list)

    # Metrics
    pass_count: int = 0
    fail_count: int = 0
    inconclusive_count: int = 0

    # Errors encountered
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class ReplayHarness:
    """
    Orchestrates replay of historical signals through policy evaluation.

    Key features:
    - Isolated namespace (no production side effects)
    - Deterministic evaluation (same inputs = same outputs)
    - Full audit trail of evaluations and exceptions
    - Comparison support with production results
    """

    def __init__(self, db_session=None):
        """
        Initialize the replay harness.

        Args:
            db_session: Optional SQLAlchemy session for DB operations
        """
        self.db_session = db_session

    def _compute_input_hash(self, policy_version: Dict, signal: Dict) -> str:
        """Compute deterministic hash of evaluation inputs."""
        input_data = {
            "policy_version_id": policy_version.get("id"),
            "rule_definition": policy_version.get("rule_definition"),
            "signal_type": signal.get("signal_type"),
            "signal_payload": signal.get("payload"),
            "signal_timestamp": signal.get("timestamp").isoformat() if isinstance(signal.get("timestamp"), datetime) else signal.get("timestamp"),
        }
        canonical = json.dumps(input_data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _compute_fingerprint(self, policy_id: str, signal_ids: List[str], context: Dict) -> str:
        """Compute exception fingerprint for deduplication."""
        fingerprint_data = {
            "policy_id": policy_id,
            "signal_ids": sorted(signal_ids),
            "context_keys": sorted(context.keys()),
        }
        canonical = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _evaluate_threshold_breach(
        self,
        rule: Dict,
        signal: IngestedSignal
    ) -> tuple[str, Optional[str], Dict]:
        """
        Evaluate a threshold breach rule.

        Returns:
            Tuple of (result, severity, details)
        """
        conditions = rule.get("conditions", [])
        evaluation_logic = rule.get("evaluation_logic", "any_condition_met")

        condition_results = []
        triggered_severity = None

        for condition in conditions:
            # Check signal type match
            if condition.get("signal_type") != signal.signal_type:
                continue

            threshold = condition.get("threshold", {})
            field_path = threshold.get("field", "")
            operator = threshold.get("operator", ">")
            threshold_value = threshold.get("value")

            # Get actual value from signal payload
            actual_value = self._get_nested_value(signal.payload, field_path.replace("payload.", ""))

            # Get threshold value (could be a reference to another field)
            if isinstance(threshold_value, str) and threshold_value.startswith("payload."):
                threshold_value = self._get_nested_value(
                    signal.payload,
                    threshold_value.replace("payload.", "")
                )

            # Evaluate condition
            try:
                breached = self._compare_values(actual_value, operator, threshold_value)
            except (TypeError, ValueError):
                condition_results.append({
                    "condition": condition,
                    "result": "inconclusive",
                    "reason": "Unable to compare values"
                })
                continue

            condition_results.append({
                "condition": condition,
                "result": "breached" if breached else "ok",
                "actual_value": actual_value,
                "threshold_value": threshold_value,
                "operator": operator
            })

            if breached:
                # Determine severity from mapping
                severity_mapping = condition.get("severity_mapping", {"default": "medium"})
                triggered_severity = self._determine_severity(
                    signal.payload,
                    severity_mapping
                )

        # Determine overall result
        breached_conditions = [r for r in condition_results if r.get("result") == "breached"]
        inconclusive_conditions = [r for r in condition_results if r.get("result") == "inconclusive"]

        if inconclusive_conditions and not breached_conditions:
            result = "inconclusive"
        elif evaluation_logic == "any_condition_met":
            result = "fail" if breached_conditions else "pass"
        else:  # all_conditions_met
            result = "fail" if len(breached_conditions) == len(conditions) else "pass"

        details = {
            "condition_results": condition_results,
            "evaluation_logic": evaluation_logic
        }

        return result, triggered_severity, details

    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _compare_values(self, actual: Any, operator: str, threshold: Any) -> bool:
        """Compare values using the specified operator."""
        if actual is None or threshold is None:
            raise ValueError("Cannot compare None values")

        if operator == ">":
            return actual > threshold
        elif operator == ">=":
            return actual >= threshold
        elif operator == "<":
            return actual < threshold
        elif operator == "<=":
            return actual <= threshold
        elif operator == "==":
            return actual == threshold
        elif operator == "!=":
            return actual != threshold
        elif operator == "abs>":
            return abs(actual) > threshold
        elif operator == "abs>=":
            return abs(actual) >= threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")

    def _determine_severity(self, payload: Dict, severity_mapping: Dict) -> str:
        """Determine severity based on payload values and mapping rules."""
        # For now, return default severity
        # Future: implement expression evaluation for severity rules
        return severity_mapping.get("default", "medium")

    def run(
        self,
        signals: List[IngestedSignal],
        policies: List[Dict],
        config: Optional[ReplayConfig] = None
    ) -> ReplayResult:
        """
        Run replay evaluation on a set of signals.

        Args:
            signals: List of signals to evaluate
            policies: List of policy definitions with versions
            config: Optional replay configuration

        Returns:
            ReplayResult with all evaluations and metrics
        """
        config = config or ReplayConfig()
        result = ReplayResult(
            namespace=config.namespace,
            config=config
        )

        # Filter signals by date range if configured
        filtered_signals = signals
        if config.from_date:
            filtered_signals = [s for s in filtered_signals if s.timestamp >= config.from_date]
        if config.to_date:
            filtered_signals = [s for s in filtered_signals if s.timestamp <= config.to_date]

        result.signals_processed = len(filtered_signals)
        seen_fingerprints = set()

        for signal in filtered_signals:
            for policy in policies:
                # Skip if policy_ids filter is set and this policy isn't included
                if config.policy_ids and policy.get("id") not in config.policy_ids:
                    continue

                try:
                    eval_result = self._evaluate_signal(signal, policy)
                    result.evaluations.append(eval_result)

                    # Update metrics
                    if eval_result.result == "pass":
                        result.pass_count += 1
                    elif eval_result.result == "fail":
                        result.fail_count += 1

                        # Raise exception for failures
                        exception = self._create_exception(
                            policy=policy,
                            signal=signal,
                            evaluation=eval_result
                        )

                        # Dedupe by fingerprint
                        if exception.fingerprint not in seen_fingerprints:
                            seen_fingerprints.add(exception.fingerprint)
                            result.exceptions_raised.append(exception)
                    else:
                        result.inconclusive_count += 1

                except Exception as e:
                    result.errors.append({
                        "signal_id": signal.id,
                        "policy_id": policy.get("id"),
                        "error": str(e)
                    })

        result.completed_at = datetime.utcnow()
        return result

    def _evaluate_signal(
        self,
        signal: IngestedSignal,
        policy: Dict
    ) -> EvaluationResult:
        """Evaluate a single signal against a policy."""
        policy_version = policy.get("current_version", policy)
        rule_definition = policy_version.get("rule_definition", {})
        rule_type = rule_definition.get("type", "threshold_breach")

        input_hash = self._compute_input_hash(
            policy_version,
            signal.model_dump()
        )

        if rule_type == "threshold_breach":
            result, severity, details = self._evaluate_threshold_breach(
                rule_definition,
                signal
            )
        else:
            result = "inconclusive"
            severity = None
            details = {"error": f"Unknown rule type: {rule_type}"}

        return EvaluationResult(
            policy_id=policy.get("id", "unknown"),
            policy_version_id=policy_version.get("id", "unknown"),
            signal_id=signal.id,
            result=result,
            severity=severity,
            details=details,
            input_hash=input_hash
        )

    def _create_exception(
        self,
        policy: Dict,
        signal: IngestedSignal,
        evaluation: EvaluationResult
    ) -> ExceptionRaised:
        """Create an exception from a failed evaluation."""
        context = {
            "signal_type": signal.signal_type,
            "source": signal.source,
            **signal.payload
        }

        fingerprint = self._compute_fingerprint(
            policy_id=policy.get("id", "unknown"),
            signal_ids=[signal.id],
            context=context
        )

        return ExceptionRaised(
            title=f"{policy.get('name', 'Policy')} - {signal.signal_type}",
            severity=evaluation.severity or "medium",
            policy_id=policy.get("id", "unknown"),
            evaluation_id=evaluation.evaluation_id,
            signal_ids=[signal.id],
            context=context,
            fingerprint=fingerprint
        )

    def run_from_db(
        self,
        config: ReplayConfig,
        signal_ids: Optional[List[str]] = None
    ) -> ReplayResult:
        """
        Run replay using signals and policies from database.

        Args:
            config: Replay configuration
            signal_ids: Optional list of specific signal IDs to replay

        Returns:
            ReplayResult
        """
        if not self.db_session:
            raise ValueError("Database session required for run_from_db")

        from core.models import Signal, Policy, PolicyVersion

        # Load signals
        query = self.db_session.query(Signal)
        if signal_ids:
            query = query.filter(Signal.id.in_(signal_ids))
        if config.from_date:
            query = query.filter(Signal.timestamp >= config.from_date)
        if config.to_date:
            query = query.filter(Signal.timestamp <= config.to_date)

        db_signals = query.all()
        signals = [
            IngestedSignal(
                id=str(s.id),
                signal_type=s.signal_type,
                source=s.source,
                payload=s.payload,
                timestamp=s.timestamp,
                reliability=s.reliability or 1.0,
                provenance=s.signal_metadata or {}
            )
            for s in db_signals
        ]

        # Load policies with current versions
        policy_query = self.db_session.query(Policy).filter(Policy.is_active == True)
        if config.policy_ids:
            policy_query = policy_query.filter(Policy.id.in_(config.policy_ids))

        policies = []
        for p in policy_query.all():
            version = self.db_session.query(PolicyVersion).filter(
                PolicyVersion.policy_id == p.id,
                PolicyVersion.is_current == True
            ).first()

            if version:
                policies.append({
                    "id": str(p.id),
                    "name": p.name,
                    "current_version": {
                        "id": str(version.id),
                        "rule_definition": version.rule_definition
                    }
                })

        return self.run(signals, policies, config)
