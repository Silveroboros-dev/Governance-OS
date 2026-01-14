"""
Eval Runner - CI-integrated evaluation runner.

Runs all evaluations and exits with code 1 if any fail.
This ensures hallucinations and ungrounded claims fail CI.

Usage:
    python -m evals.runner           # Run all evals
    python -m evals.runner --verbose # Verbose output
    python -m evals.runner --json    # JSON output
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .validators.grounding import GroundingValidator, GroundingResult
from .validators.hallucination import HallucinationDetector, HallucinationResult
from coprocessor.schemas.narrative import (
    NarrativeMemo,
    NarrativeClaim,
    EvidenceReference,
    MemoSection,
)


class TestCaseResult(BaseModel):
    """Result of running a single test case."""

    case_id: str
    case_name: str
    expected_result: str
    actual_result: str
    passed: bool
    grounding_result: Optional[GroundingResult] = None
    hallucination_result: Optional[HallucinationResult] = None
    error_message: Optional[str] = None
    duration_ms: float = 0


class EvalRunResult(BaseModel):
    """Overall result of the evaluation run."""

    run_id: str = Field(default_factory=lambda: f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0

    results: List[TestCaseResult] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_cases == 0:
            return 100.0
        return (self.passed_cases / self.total_cases) * 100

    @property
    def all_passed(self) -> bool:
        return self.failed_cases == 0


class EvalRunner:
    """
    Runs evaluation test cases and reports results.

    Exit codes:
    - 0: All tests passed
    - 1: One or more tests failed
    """

    def __init__(
        self,
        datasets_path: Optional[Path] = None,
        strict_grounding: bool = True,
    ):
        """
        Initialize the runner.

        Args:
            datasets_path: Path to datasets directory
            strict_grounding: If True, invalid evidence refs fail grounding
        """
        self.datasets_path = datasets_path or Path(__file__).parent / "datasets"
        self.strict_grounding = strict_grounding

        self.grounding_validator = GroundingValidator(strict=strict_grounding)
        self.hallucination_detector = HallucinationDetector(check_grounding=True)

    def load_goldens(self, filename: str = "narrative_goldens.json") -> List[Dict[str, Any]]:
        """Load golden test cases from JSON file."""
        filepath = self.datasets_path / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Golden dataset not found: {filepath}")

        with open(filepath, "r") as f:
            data = json.load(f)

        return data.get("test_cases", [])

    def _build_memo_from_dict(self, memo_dict: Dict[str, Any]) -> NarrativeMemo:
        """Convert a dictionary to a NarrativeMemo object."""
        sections = []
        for section_data in memo_dict.get("sections", []):
            claims = []
            for claim_data in section_data.get("claims", []):
                evidence_refs = []
                for ref_data in claim_data.get("evidence_refs", []):
                    evidence_refs.append(EvidenceReference(
                        evidence_id=ref_data.get("evidence_id", ""),
                        evidence_type=ref_data.get("evidence_type", "unknown"),
                    ))
                claims.append(NarrativeClaim(
                    text=claim_data.get("text", ""),
                    evidence_refs=evidence_refs,
                ))
            sections.append(MemoSection(
                heading=section_data.get("heading", ""),
                claims=claims,
            ))

        return NarrativeMemo(
            decision_id=memo_dict.get("decision_id", ""),
            title=memo_dict.get("title", ""),
            sections=sections,
        )

    def run_case(self, case: Dict[str, Any]) -> TestCaseResult:
        """Run a single test case."""
        import time
        start_time = time.time()

        case_id = case.get("id", "unknown")
        case_name = case.get("name", "Unnamed")
        expected_result = case.get("expected_result", "pass")
        expected_error_type = case.get("expected_error_type")

        try:
            # Build memo and evidence pack
            memo_dict = case.get("memo", {})

            # Handle empty evidence refs - this should fail validation
            try:
                memo = self._build_memo_from_dict(memo_dict)
            except ValueError as e:
                # Empty evidence refs cause validation error in NarrativeClaim
                if expected_result == "fail" and expected_error_type == "ungrounded_claim":
                    return TestCaseResult(
                        case_id=case_id,
                        case_name=case_name,
                        expected_result=expected_result,
                        actual_result="fail",
                        passed=True,  # Expected failure occurred
                        error_message=str(e),
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                raise

            evidence_pack = case.get("evidence_pack", {})

            # Run grounding validation
            grounding_result = self.grounding_validator.validate(memo, evidence_pack)

            # Run hallucination detection
            hallucination_result = self.hallucination_detector.detect(memo)

            # Determine actual result
            if not grounding_result.passed or not hallucination_result.passed:
                actual_result = "fail"

                # Check if failure matches expected error type
                if expected_error_type:
                    error_types_found = set()
                    for err in grounding_result.errors:
                        error_types_found.add(getattr(err, 'error_type', 'unknown'))
                    for err in hallucination_result.errors:
                        error_types_found.add(err.error_type)

                    if expected_error_type not in error_types_found:
                        # Wrong type of failure
                        return TestCaseResult(
                            case_id=case_id,
                            case_name=case_name,
                            expected_result=expected_result,
                            actual_result=actual_result,
                            passed=False,
                            grounding_result=grounding_result,
                            hallucination_result=hallucination_result,
                            error_message=f"Expected error type '{expected_error_type}' but found {error_types_found}",
                            duration_ms=(time.time() - start_time) * 1000,
                        )
            else:
                actual_result = "pass"

            # Check if result matches expectation
            passed = (actual_result == expected_result)

            return TestCaseResult(
                case_id=case_id,
                case_name=case_name,
                expected_result=expected_result,
                actual_result=actual_result,
                passed=passed,
                grounding_result=grounding_result,
                hallucination_result=hallucination_result,
                duration_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return TestCaseResult(
                case_id=case_id,
                case_name=case_name,
                expected_result=expected_result,
                actual_result="error",
                passed=False,
                error_message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

    def run_all(self, verbose: bool = False) -> EvalRunResult:
        """
        Run all golden test cases.

        Args:
            verbose: Print detailed output

        Returns:
            EvalRunResult with all results
        """
        result = EvalRunResult()
        cases = self.load_goldens()
        result.total_cases = len(cases)

        if verbose:
            print(f"\nRunning {len(cases)} evaluation cases...")
            print("=" * 60)

        for case in cases:
            case_result = self.run_case(case)
            result.results.append(case_result)

            if case_result.passed:
                result.passed_cases += 1
                status = "PASS"
            else:
                result.failed_cases += 1
                status = "FAIL"

            if verbose:
                print(f"[{status}] {case_result.case_name}")
                if not case_result.passed:
                    print(f"       Expected: {case_result.expected_result}")
                    print(f"       Actual: {case_result.actual_result}")
                    if case_result.error_message:
                        print(f"       Error: {case_result.error_message}")

        result.completed_at = datetime.utcnow()

        if verbose:
            print("=" * 60)
            print(f"\nResults: {result.passed_cases}/{result.total_cases} passed ({result.success_rate:.1f}%)")
            if result.failed_cases > 0:
                print(f"FAILED: {result.failed_cases} case(s)")

        return result

    def run_and_exit(self, verbose: bool = False, json_output: bool = False) -> int:
        """
        Run all evals and return exit code for CI.

        Args:
            verbose: Print detailed output
            json_output: Output JSON instead of text

        Returns:
            0 if all passed, 1 if any failed
        """
        result = self.run_all(verbose=verbose and not json_output)

        if json_output:
            print(result.model_dump_json(indent=2))
        elif not verbose:
            # Minimal output
            if result.all_passed:
                print(f"All {result.total_cases} evaluations passed")
            else:
                print(f"FAILED: {result.failed_cases}/{result.total_cases} evaluations failed")
                for case_result in result.results:
                    if not case_result.passed:
                        print(f"  - {case_result.case_name}: {case_result.error_message or 'unexpected result'}")

        return 0 if result.all_passed else 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="evals",
        description="Run Governance OS evaluations (fails CI on hallucinations)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--dataset",
        default="narrative_goldens.json",
        help="Dataset file to use"
    )

    args = parser.parse_args()

    runner = EvalRunner()
    exit_code = runner.run_and_exit(
        verbose=args.verbose,
        json_output=args.json
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
