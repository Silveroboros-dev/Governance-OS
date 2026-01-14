"""
Comparison Module - Compare replay results with production.

Enables before/after analysis for policy tuning and verification
of deterministic behavior.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .harness import EvaluationResult, ReplayResult


class EvaluationDiff(BaseModel):
    """Difference between two evaluations of the same input."""

    signal_id: str
    policy_id: str
    input_hash: str

    # Results
    baseline_result: str
    comparison_result: str
    result_changed: bool

    # Severity changes
    baseline_severity: Optional[str] = None
    comparison_severity: Optional[str] = None
    severity_changed: bool = False

    # Details
    baseline_details: Dict[str, Any] = Field(default_factory=dict)
    comparison_details: Dict[str, Any] = Field(default_factory=dict)


class ComparisonResult(BaseModel):
    """Result of comparing two replay runs or replay vs production."""

    comparison_id: str = Field(default_factory=lambda: str(__import__("uuid").uuid4()))
    compared_at: datetime = Field(default_factory=datetime.utcnow)

    # Source identification
    baseline_id: str
    comparison_id_ref: str
    baseline_namespace: str
    comparison_namespace: str

    # Summary metrics
    total_evaluations: int = 0
    matching_evaluations: int = 0
    divergent_evaluations: int = 0
    baseline_only: int = 0
    comparison_only: int = 0

    # Determinism check
    is_deterministic: bool = True
    determinism_failures: List[str] = Field(default_factory=list)

    # Detailed diffs
    diffs: List[EvaluationDiff] = Field(default_factory=list)

    # Exception comparison
    baseline_exception_count: int = 0
    comparison_exception_count: int = 0
    new_exceptions: int = 0
    resolved_exceptions: int = 0

    @property
    def match_rate(self) -> float:
        """Calculate the percentage of matching evaluations."""
        if self.total_evaluations == 0:
            return 100.0
        return (self.matching_evaluations / self.total_evaluations) * 100


def compare_evaluations(
    baseline: ReplayResult,
    comparison: ReplayResult,
    check_determinism: bool = True
) -> ComparisonResult:
    """
    Compare two replay results.

    Args:
        baseline: The baseline replay result (e.g., production or previous run)
        comparison: The comparison replay result (e.g., replay or new policy version)
        check_determinism: If True, verify that same inputs produce same outputs

    Returns:
        ComparisonResult with detailed comparison metrics
    """
    result = ComparisonResult(
        baseline_id=baseline.replay_id,
        comparison_id_ref=comparison.replay_id,
        baseline_namespace=baseline.namespace,
        comparison_namespace=comparison.namespace
    )

    # Index baseline evaluations by (signal_id, policy_id)
    baseline_index: Dict[tuple, EvaluationResult] = {}
    for eval in baseline.evaluations:
        key = (eval.signal_id, eval.policy_id)
        baseline_index[key] = eval

    # Index comparison evaluations
    comparison_index: Dict[tuple, EvaluationResult] = {}
    for eval in comparison.evaluations:
        key = (eval.signal_id, eval.policy_id)
        comparison_index[key] = eval

    # Find all unique keys
    all_keys = set(baseline_index.keys()) | set(comparison_index.keys())
    result.total_evaluations = len(all_keys)

    for key in all_keys:
        baseline_eval = baseline_index.get(key)
        comparison_eval = comparison_index.get(key)

        if baseline_eval and comparison_eval:
            # Both exist - compare them
            result_changed = baseline_eval.result != comparison_eval.result
            severity_changed = baseline_eval.severity != comparison_eval.severity

            if result_changed or severity_changed:
                result.divergent_evaluations += 1
                result.diffs.append(EvaluationDiff(
                    signal_id=key[0],
                    policy_id=key[1],
                    input_hash=baseline_eval.input_hash,
                    baseline_result=baseline_eval.result,
                    comparison_result=comparison_eval.result,
                    result_changed=result_changed,
                    baseline_severity=baseline_eval.severity,
                    comparison_severity=comparison_eval.severity,
                    severity_changed=severity_changed,
                    baseline_details=baseline_eval.details,
                    comparison_details=comparison_eval.details
                ))

                # Check determinism
                if check_determinism and baseline_eval.input_hash == comparison_eval.input_hash:
                    if result_changed:
                        result.is_deterministic = False
                        result.determinism_failures.append(
                            f"Same input hash {baseline_eval.input_hash[:16]}... produced different results"
                        )
            else:
                result.matching_evaluations += 1

        elif baseline_eval:
            result.baseline_only += 1
        else:
            result.comparison_only += 1

    # Compare exceptions
    baseline_fingerprints = {e.fingerprint for e in baseline.exceptions_raised}
    comparison_fingerprints = {e.fingerprint for e in comparison.exceptions_raised}

    result.baseline_exception_count = len(baseline.exceptions_raised)
    result.comparison_exception_count = len(comparison.exceptions_raised)
    result.new_exceptions = len(comparison_fingerprints - baseline_fingerprints)
    result.resolved_exceptions = len(baseline_fingerprints - comparison_fingerprints)

    return result


def compare_with_production(
    replay_result: ReplayResult,
    db_session,
    namespace: str = "production"
) -> ComparisonResult:
    """
    Compare replay result with production evaluations from database.

    Args:
        replay_result: The replay result to compare
        db_session: SQLAlchemy database session
        namespace: Production namespace to compare against

    Returns:
        ComparisonResult comparing replay vs production
    """
    from core.models import Evaluation, Exception as DBException

    # Load production evaluations for the same signals
    signal_ids = list({e.signal_id for e in replay_result.evaluations})

    production_evals = db_session.query(Evaluation).filter(
        Evaluation.signal_id.in_(signal_ids),
        Evaluation.replay_namespace == namespace
    ).all()

    # Convert to ReplayResult format
    production_result = ReplayResult(
        replay_id="production",
        namespace=namespace,
        config=replay_result.config
    )

    for eval in production_evals:
        production_result.evaluations.append(EvaluationResult(
            evaluation_id=str(eval.id),
            policy_id=str(eval.policy_id),
            policy_version_id=str(eval.policy_version_id),
            signal_id=str(eval.signal_id),
            result=eval.result.value if hasattr(eval.result, 'value') else eval.result,
            severity=eval.severity.value if eval.severity and hasattr(eval.severity, 'value') else eval.severity,
            details=eval.details or {},
            input_hash=eval.input_hash or "",
            evaluated_at=eval.evaluated_at
        ))

    # Load production exceptions
    production_exceptions = db_session.query(DBException).filter(
        DBException.id.in_([
            e.exception_id for e in production_result.evaluations
            if hasattr(e, 'exception_id')
        ])
    ).all()

    production_result.exceptions_raised = [
        {
            "fingerprint": exc.fingerprint,
            "policy_id": str(exc.policy_id),
            "severity": exc.severity.value if hasattr(exc.severity, 'value') else exc.severity
        }
        for exc in production_exceptions
    ]

    return compare_evaluations(production_result, replay_result)


def generate_comparison_report(comparison: ComparisonResult) -> str:
    """
    Generate a human-readable comparison report.

    Args:
        comparison: ComparisonResult to report on

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 60,
        "REPLAY COMPARISON REPORT",
        "=" * 60,
        "",
        f"Compared at: {comparison.compared_at.isoformat()}",
        f"Baseline: {comparison.baseline_namespace} ({comparison.baseline_id[:8]}...)",
        f"Comparison: {comparison.comparison_namespace} ({comparison.comparison_id_ref[:8]}...)",
        "",
        "-" * 40,
        "SUMMARY",
        "-" * 40,
        f"Total evaluations: {comparison.total_evaluations}",
        f"Matching: {comparison.matching_evaluations} ({comparison.match_rate:.1f}%)",
        f"Divergent: {comparison.divergent_evaluations}",
        f"Baseline only: {comparison.baseline_only}",
        f"Comparison only: {comparison.comparison_only}",
        "",
        "-" * 40,
        "DETERMINISM CHECK",
        "-" * 40,
        f"Is deterministic: {'YES' if comparison.is_deterministic else 'NO'}",
    ]

    if comparison.determinism_failures:
        lines.append("Failures:")
        for failure in comparison.determinism_failures[:5]:
            lines.append(f"  - {failure}")
        if len(comparison.determinism_failures) > 5:
            lines.append(f"  ... and {len(comparison.determinism_failures) - 5} more")

    lines.extend([
        "",
        "-" * 40,
        "EXCEPTIONS",
        "-" * 40,
        f"Baseline exceptions: {comparison.baseline_exception_count}",
        f"Comparison exceptions: {comparison.comparison_exception_count}",
        f"New exceptions: {comparison.new_exceptions}",
        f"Resolved exceptions: {comparison.resolved_exceptions}",
    ])

    if comparison.diffs:
        lines.extend([
            "",
            "-" * 40,
            f"DIVERGENT EVALUATIONS (showing first 10 of {len(comparison.diffs)})",
            "-" * 40,
        ])
        for diff in comparison.diffs[:10]:
            lines.append(f"  Signal: {diff.signal_id[:8]}... Policy: {diff.policy_id[:8]}...")
            lines.append(f"    Result: {diff.baseline_result} -> {diff.comparison_result}")
            if diff.severity_changed:
                lines.append(f"    Severity: {diff.baseline_severity} -> {diff.comparison_severity}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
