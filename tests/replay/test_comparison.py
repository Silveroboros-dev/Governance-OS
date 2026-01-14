"""
Tests for Replay Comparison - Compare replay results.
"""

import pytest
from datetime import datetime

from replay.comparison import (
    compare_evaluations,
    ComparisonResult,
    EvaluationDiff,
    generate_comparison_report,
)
from replay.harness import ReplayResult, EvaluationResult, ExceptionRaised


class TestCompareEvaluations:
    """Tests for compare_evaluations function."""

    @pytest.fixture
    def baseline_result(self):
        """Create a baseline replay result."""
        result = ReplayResult(
            replay_id="baseline_001",
            namespace="production",
        )
        result.evaluations = [
            EvaluationResult(
                evaluation_id="eval_001",
                policy_id="policy-001",
                policy_version_id="version-001",
                signal_id="signal-001",
                result="pass",
                severity=None,
                input_hash="hash_001",
            ),
            EvaluationResult(
                evaluation_id="eval_002",
                policy_id="policy-001",
                policy_version_id="version-001",
                signal_id="signal-002",
                result="fail",
                severity="high",
                input_hash="hash_002",
            ),
        ]
        result.exceptions_raised = [
            ExceptionRaised(
                exception_id="exc_001",
                title="Test Exception",
                severity="high",
                policy_id="policy-001",
                evaluation_id="eval_002",
                signal_ids=["signal-002"],
                context={},
                fingerprint="fp_001",
            )
        ]
        return result

    @pytest.fixture
    def matching_comparison(self, baseline_result):
        """Create a comparison result that matches baseline."""
        result = ReplayResult(
            replay_id="comparison_001",
            namespace="replay",
        )
        # Same evaluations
        result.evaluations = [
            EvaluationResult(
                evaluation_id="eval_003",
                policy_id="policy-001",
                policy_version_id="version-001",
                signal_id="signal-001",
                result="pass",
                severity=None,
                input_hash="hash_001",
            ),
            EvaluationResult(
                evaluation_id="eval_004",
                policy_id="policy-001",
                policy_version_id="version-001",
                signal_id="signal-002",
                result="fail",
                severity="high",
                input_hash="hash_002",
            ),
        ]
        result.exceptions_raised = [
            ExceptionRaised(
                exception_id="exc_002",
                title="Test Exception",
                severity="high",
                policy_id="policy-001",
                evaluation_id="eval_004",
                signal_ids=["signal-002"],
                context={},
                fingerprint="fp_001",  # Same fingerprint
            )
        ]
        return result

    @pytest.fixture
    def divergent_comparison(self, baseline_result):
        """Create a comparison result that diverges from baseline."""
        result = ReplayResult(
            replay_id="comparison_002",
            namespace="replay",
        )
        result.evaluations = [
            EvaluationResult(
                evaluation_id="eval_005",
                policy_id="policy-001",
                policy_version_id="version-001",
                signal_id="signal-001",
                result="fail",  # Changed from pass
                severity="medium",
                input_hash="hash_001",
            ),
            EvaluationResult(
                evaluation_id="eval_006",
                policy_id="policy-001",
                policy_version_id="version-001",
                signal_id="signal-002",
                result="fail",
                severity="critical",  # Changed from high
                input_hash="hash_002",
            ),
        ]
        return result

    def test_compare_matching_results(self, baseline_result, matching_comparison):
        """Test comparing identical results."""
        comparison = compare_evaluations(baseline_result, matching_comparison)

        assert comparison.total_evaluations == 2
        assert comparison.matching_evaluations == 2
        assert comparison.divergent_evaluations == 0
        assert comparison.is_deterministic is True
        assert comparison.match_rate == 100.0

    def test_compare_divergent_results(self, baseline_result, divergent_comparison):
        """Test comparing divergent results."""
        comparison = compare_evaluations(baseline_result, divergent_comparison)

        assert comparison.total_evaluations == 2
        assert comparison.divergent_evaluations == 2
        assert comparison.matching_evaluations == 0
        assert len(comparison.diffs) == 2

    def test_determinism_check(self, baseline_result, divergent_comparison):
        """Test determinism detection."""
        comparison = compare_evaluations(
            baseline_result,
            divergent_comparison,
            check_determinism=True
        )

        # Same input hash but different results = non-deterministic
        assert comparison.is_deterministic is False
        assert len(comparison.determinism_failures) > 0

    def test_exception_comparison(self, baseline_result, matching_comparison):
        """Test exception count comparison."""
        comparison = compare_evaluations(baseline_result, matching_comparison)

        assert comparison.baseline_exception_count == 1
        assert comparison.comparison_exception_count == 1
        assert comparison.new_exceptions == 0
        assert comparison.resolved_exceptions == 0

    def test_new_exceptions_detected(self, baseline_result):
        """Test detection of new exceptions."""
        comparison_result = ReplayResult(
            replay_id="comparison_003",
            namespace="replay",
        )
        comparison_result.evaluations = baseline_result.evaluations.copy()
        comparison_result.exceptions_raised = [
            ExceptionRaised(
                exception_id="exc_new",
                title="New Exception",
                severity="high",
                policy_id="policy-001",
                evaluation_id="eval_002",
                signal_ids=["signal-002"],
                context={},
                fingerprint="fp_new",  # New fingerprint
            )
        ]

        comparison = compare_evaluations(baseline_result, comparison_result)

        assert comparison.new_exceptions == 1
        assert comparison.resolved_exceptions == 1  # Original exception "resolved"

    def test_baseline_only_evaluations(self, baseline_result):
        """Test detection of baseline-only evaluations."""
        comparison_result = ReplayResult(
            replay_id="comparison_004",
            namespace="replay",
        )
        # Only has first evaluation
        comparison_result.evaluations = [baseline_result.evaluations[0]]

        comparison = compare_evaluations(baseline_result, comparison_result)

        assert comparison.baseline_only == 1
        assert comparison.comparison_only == 0


class TestComparisonResult:
    """Tests for ComparisonResult model."""

    def test_match_rate_calculation(self):
        """Test match rate property."""
        result = ComparisonResult(
            baseline_id="b1",
            comparison_id_ref="c1",
            baseline_namespace="prod",
            comparison_namespace="replay",
            total_evaluations=10,
            matching_evaluations=8,
            divergent_evaluations=2,
        )

        assert result.match_rate == 80.0

    def test_match_rate_zero_evaluations(self):
        """Test match rate with zero evaluations."""
        result = ComparisonResult(
            baseline_id="b1",
            comparison_id_ref="c1",
            baseline_namespace="prod",
            comparison_namespace="replay",
            total_evaluations=0,
        )

        assert result.match_rate == 100.0  # Default to 100% if no evaluations


class TestEvaluationDiff:
    """Tests for EvaluationDiff model."""

    def test_diff_creation(self):
        """Test creating an evaluation diff."""
        diff = EvaluationDiff(
            signal_id="signal-001",
            policy_id="policy-001",
            input_hash="hash_001",
            baseline_result="pass",
            comparison_result="fail",
            result_changed=True,
            baseline_severity=None,
            comparison_severity="high",
            severity_changed=True,
        )

        assert diff.result_changed is True
        assert diff.severity_changed is True


class TestGenerateComparisonReport:
    """Tests for report generation."""

    def test_generate_report(self):
        """Test generating a comparison report."""
        result = ComparisonResult(
            baseline_id="baseline_001",
            comparison_id_ref="comparison_001",
            baseline_namespace="production",
            comparison_namespace="replay",
            total_evaluations=100,
            matching_evaluations=95,
            divergent_evaluations=5,
            is_deterministic=True,
        )

        report = generate_comparison_report(result)

        assert "REPLAY COMPARISON REPORT" in report
        assert "production" in report
        assert "replay" in report
        assert "100" in report
        assert "95.0%" in report

    def test_report_with_failures(self):
        """Test report with determinism failures."""
        result = ComparisonResult(
            baseline_id="b1",
            comparison_id_ref="c1",
            baseline_namespace="prod",
            comparison_namespace="replay",
            total_evaluations=10,
            matching_evaluations=5,
            divergent_evaluations=5,
            is_deterministic=False,
            determinism_failures=["Failure 1", "Failure 2"],
        )

        report = generate_comparison_report(result)

        assert "NO" in report  # Is deterministic: NO
        assert "Failure 1" in report
