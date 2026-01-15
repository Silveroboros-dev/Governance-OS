"""
Kernel Regression Evaluator - Sprint 3

Verifies deterministic kernel outputs by replaying historical decisions.
Detects policy drift when replay results don't match original outcomes.

CRITICAL: If this eval fails, the kernel's determinism guarantee is broken.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReplayMismatch(BaseModel):
    """Details of a mismatch between original and replayed result."""
    decision_id: str
    field: str
    original_value: Any
    replayed_value: Any
    notes: Optional[str]


class ReplayResult(BaseModel):
    """Result of replaying a single historical decision."""
    decision_id: str
    matched: bool
    original_result: str  # pass, fail, exception_raised
    replayed_result: str
    mismatches: List[ReplayMismatch] = Field(default_factory=list)
    error: Optional[str] = None


class RegressionEvalResult(BaseModel):
    """Result of kernel regression evaluation."""

    run_id: str = Field(default_factory=lambda: f"regression_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Counts
    total_decisions: int = 0
    matching_count: int = 0
    mismatch_count: int = 0
    error_count: int = 0

    # Results
    results: List[ReplayResult] = Field(default_factory=list)
    mismatch_details: List[ReplayMismatch] = Field(default_factory=list)

    @property
    def drift_detected(self) -> bool:
        """Check if policy drift was detected."""
        return self.mismatch_count > 0

    @property
    def passed(self) -> bool:
        """Regression passes only if 100% match."""
        return not self.drift_detected and self.error_count == 0


class RegressionEvaluator:
    """
    Evaluates kernel determinism by replaying historical decisions.

    For the kernel's determinism guarantee to hold:
    - Same signals + same policy version → same evaluation result
    - Replay must produce identical exceptions and options

    This eval should ALWAYS pass. Any failure indicates a regression.
    """

    def __init__(
        self,
        datasets_path: Optional[Path] = None,
    ):
        """
        Initialize evaluator.

        Args:
            datasets_path: Path to datasets directory
        """
        self.datasets_path = datasets_path or Path(__file__).parent.parent / "datasets"

    def load_historical_pack(self, pack: str) -> List[Dict[str, Any]]:
        """Load historical decisions for a pack."""
        filename = f"{pack}_historical.json"
        filepath = self.datasets_path / filename

        if not filepath.exists():
            return []

        with open(filepath, "r") as f:
            data = json.load(f)

        return data.get("decisions", [])

    def _compare_results(
        self,
        original: Dict[str, Any],
        replayed: Dict[str, Any],
        decision_id: str,
    ) -> List[ReplayMismatch]:
        """Compare original and replayed evaluation results."""
        mismatches = []

        # Compare evaluation result
        orig_result = original.get("evaluation_result")
        replay_result = replayed.get("evaluation_result")
        if orig_result != replay_result:
            mismatches.append(ReplayMismatch(
                decision_id=decision_id,
                field="evaluation_result",
                original_value=orig_result,
                replayed_value=replay_result,
                notes="Evaluation result mismatch"
            ))

        # Compare exception severity if applicable
        if orig_result == "exception_raised":
            orig_severity = original.get("exception", {}).get("severity")
            replay_severity = replayed.get("exception", {}).get("severity")
            if orig_severity != replay_severity:
                mismatches.append(ReplayMismatch(
                    decision_id=decision_id,
                    field="exception.severity",
                    original_value=orig_severity,
                    replayed_value=replay_severity,
                    notes="Exception severity mismatch"
                ))

            # Compare option count
            orig_options = len(original.get("exception", {}).get("options", []))
            replay_options = len(replayed.get("exception", {}).get("options", []))
            if orig_options != replay_options:
                mismatches.append(ReplayMismatch(
                    decision_id=decision_id,
                    field="exception.options.count",
                    original_value=orig_options,
                    replayed_value=replay_options,
                    notes="Option count mismatch"
                ))

        # Compare input hash (should be deterministic)
        orig_hash = original.get("input_hash")
        replay_hash = replayed.get("input_hash")
        if orig_hash and replay_hash and orig_hash != replay_hash:
            mismatches.append(ReplayMismatch(
                decision_id=decision_id,
                field="input_hash",
                original_value=orig_hash,
                replayed_value=replay_hash,
                notes="Input hash mismatch indicates non-deterministic signal processing"
            ))

        return mismatches

    def replay_decision(
        self,
        historical: Dict[str, Any],
        evaluator_func,
    ) -> ReplayResult:
        """
        Replay a historical decision through the kernel.

        Args:
            historical: Historical decision record
            evaluator_func: Function to evaluate signals against policy

        Returns:
            ReplayResult
        """
        decision_id = historical.get("decision_id", "unknown")

        try:
            # Extract original signals and policy version
            signals = historical.get("signals", [])
            policy_version_id = historical.get("policy_version_id")
            original_result = historical.get("evaluation_result", "unknown")

            # Replay through evaluator
            replay_output = evaluator_func(
                signals=signals,
                policy_version_id=policy_version_id,
            )

            replayed_result = replay_output.get("evaluation_result", "unknown")

            # Compare results
            mismatches = self._compare_results(
                original=historical,
                replayed=replay_output,
                decision_id=decision_id,
            )

            return ReplayResult(
                decision_id=decision_id,
                matched=len(mismatches) == 0,
                original_result=original_result,
                replayed_result=replayed_result,
                mismatches=mismatches,
            )

        except Exception as e:
            return ReplayResult(
                decision_id=decision_id,
                matched=False,
                original_result=historical.get("evaluation_result", "unknown"),
                replayed_result="error",
                error=str(e),
            )

    def evaluate(
        self,
        pack: str,
        evaluator_func,
        verbose: bool = False,
    ) -> RegressionEvalResult:
        """
        Run kernel regression evaluation.

        Args:
            pack: Pack to evaluate
            evaluator_func: Function to evaluate signals against policy
            verbose: Print detailed output

        Returns:
            RegressionEvalResult
        """
        result = RegressionEvalResult()

        historical = self.load_historical_pack(pack)
        result.total_decisions = len(historical)

        if verbose:
            print(f"\nReplaying {len(historical)} {pack} historical decisions...")
            print("=" * 60)

        for record in historical:
            replay_result = self.replay_decision(record, evaluator_func)
            result.results.append(replay_result)

            if replay_result.error:
                result.error_count += 1
                if verbose:
                    print(f"[ERROR] {replay_result.decision_id}: {replay_result.error}")
            elif replay_result.matched:
                result.matching_count += 1
                if verbose:
                    print(f"[MATCH] {replay_result.decision_id}")
            else:
                result.mismatch_count += 1
                result.mismatch_details.extend(replay_result.mismatches)
                if verbose:
                    print(f"[DRIFT] {replay_result.decision_id}")
                    for mismatch in replay_result.mismatches:
                        print(f"        {mismatch.field}: {mismatch.original_value} → {mismatch.replayed_value}")

        result.completed_at = datetime.utcnow()

        if verbose:
            print("=" * 60)
            print(f"\nResults:")
            print(f"  Total: {result.total_decisions}")
            print(f"  Matching: {result.matching_count}")
            print(f"  Mismatches: {result.mismatch_count}")
            print(f"  Errors: {result.error_count}")
            print(f"\nDrift Detected: {'YES - REGRESSION' if result.drift_detected else 'No'}")
            print(f"Overall: {'PASS' if result.passed else 'FAIL'}")

        return result


def dummy_evaluator(signals: List[Dict], policy_version_id: str) -> Dict[str, Any]:
    """
    Dummy evaluator for testing.

    In production, this would call the actual kernel evaluator.
    """
    # This is a placeholder - the real implementation would
    # evaluate signals against the policy version
    return {
        "evaluation_result": "pass",
        "input_hash": "dummy_hash",
    }
