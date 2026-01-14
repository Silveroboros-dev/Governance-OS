"""
Tests for Replay Metrics - Exception budgets and analytics.
"""

import pytest
from datetime import datetime, timedelta

from replay.metrics import (
    ExceptionBudget,
    BudgetStatus,
    PolicyMetrics,
    ReplayMetrics,
    MetricsCalculator,
    generate_metrics_report,
)
from replay.harness import ReplayResult, ReplayConfig, EvaluationResult, ExceptionRaised


class TestExceptionBudget:
    """Tests for ExceptionBudget configuration."""

    def test_default_budget(self):
        """Test default budget values."""
        budget = ExceptionBudget()

        assert budget.policy_id is None  # All policies
        assert budget.severity is None  # All severities
        assert budget.max_exceptions_per_day == 10
        assert budget.max_exceptions_per_week == 50
        assert budget.warning_threshold_percent == 80.0

    def test_custom_budget(self):
        """Test custom budget configuration."""
        budget = ExceptionBudget(
            policy_id="policy-001",
            severity="high",
            max_exceptions_per_day=5,
            max_exceptions_per_week=25,
            warning_threshold_percent=70.0,
        )

        assert budget.policy_id == "policy-001"
        assert budget.severity == "high"
        assert budget.max_exceptions_per_day == 5


class TestBudgetStatus:
    """Tests for BudgetStatus model."""

    def test_budget_status_properties(self):
        """Test budget status calculated properties."""
        budget = ExceptionBudget(max_exceptions_per_day=10)
        status = BudgetStatus(
            budget=budget,
            period="day",
            current_count=8,
            max_allowed=10,
            utilization_percent=80.0,
            is_exceeded=False,
            is_warning=True,
        )

        assert status.remaining == 2
        assert status.is_warning is True
        assert status.is_exceeded is False

    def test_budget_exceeded(self):
        """Test exceeded budget status."""
        budget = ExceptionBudget(max_exceptions_per_day=10)
        status = BudgetStatus(
            budget=budget,
            period="day",
            current_count=12,
            max_allowed=10,
            utilization_percent=120.0,
            is_exceeded=True,
            is_warning=True,
        )

        assert status.remaining == 0
        assert status.is_exceeded is True


class TestMetricsCalculator:
    """Tests for MetricsCalculator class."""

    @pytest.fixture
    def sample_replay_result(self):
        """Create a sample replay result for metrics calculation."""
        result = ReplayResult(
            replay_id="metrics_test",
            namespace="test",
            config=ReplayConfig(
                from_date=datetime(2025, 1, 1),
                to_date=datetime(2025, 1, 31),
            ),
        )

        # Add evaluations
        result.evaluations = [
            EvaluationResult(
                policy_id="policy-001",
                policy_version_id="v1",
                signal_id=f"sig_{i}",
                result="pass" if i % 3 != 0 else "fail",
                severity="high" if i % 3 == 0 else None,
                input_hash=f"hash_{i}",
            )
            for i in range(30)
        ]

        result.pass_count = 20
        result.fail_count = 10
        result.signals_processed = 30

        # Add exceptions for failures
        result.exceptions_raised = [
            ExceptionRaised(
                exception_id=f"exc_{i}",
                title=f"Exception {i}",
                severity="high" if i % 2 == 0 else "medium",
                policy_id="policy-001",
                evaluation_id=f"eval_{i}",
                signal_ids=[f"sig_{i}"],
                context={},
                fingerprint=f"fp_{i}",
            )
            for i in range(10)
        ]

        return result

    def test_calculator_initialization(self):
        """Test calculator with budgets."""
        budgets = [
            ExceptionBudget(max_exceptions_per_day=5),
        ]
        calculator = MetricsCalculator(budgets=budgets)

        assert len(calculator.budgets) == 1

    def test_calculate_basic_metrics(self, sample_replay_result):
        """Test basic metrics calculation."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate(sample_replay_result)

        assert metrics.total_signals == 30
        assert metrics.total_evaluations == 30
        assert metrics.pass_count == 20
        assert metrics.fail_count == 10
        assert metrics.total_exceptions == 10

    def test_calculate_rates(self, sample_replay_result):
        """Test rate calculations."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate(sample_replay_result)

        # Pass rate should be ~66.7%
        assert 66 <= metrics.overall_pass_rate <= 67
        # Fail rate should be ~33.3%
        assert 33 <= metrics.overall_fail_rate <= 34

    def test_calculate_days_covered(self, sample_replay_result):
        """Test days covered calculation."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate(sample_replay_result)

        assert metrics.days_covered == 30  # Jan 1-31

    def test_exceptions_by_severity(self, sample_replay_result):
        """Test severity breakdown."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate(sample_replay_result)

        assert "high" in metrics.exceptions_by_severity
        assert "medium" in metrics.exceptions_by_severity
        total = sum(metrics.exceptions_by_severity.values())
        assert total == 10

    def test_policy_metrics(self, sample_replay_result):
        """Test per-policy metrics."""
        calculator = MetricsCalculator()
        metrics = calculator.calculate(sample_replay_result)

        assert len(metrics.policy_metrics) > 0

        for pm in metrics.policy_metrics:
            assert pm.total_evaluations > 0
            assert pm.pass_rate + pm.fail_rate <= 100

    def test_budget_status_calculation(self, sample_replay_result):
        """Test budget status calculation."""
        budgets = [
            ExceptionBudget(
                max_exceptions_per_day=5,
                max_exceptions_per_week=30,
                warning_threshold_percent=80.0,
            ),
        ]
        calculator = MetricsCalculator(budgets=budgets)
        metrics = calculator.calculate(sample_replay_result)

        # Should have daily and weekly status for each budget
        assert len(metrics.budget_statuses) == 2

    def test_empty_result_handling(self):
        """Test handling of empty replay result."""
        result = ReplayResult(namespace="empty")
        calculator = MetricsCalculator()

        metrics = calculator.calculate(result)

        assert metrics.total_signals == 0
        assert metrics.overall_pass_rate == 0.0
        assert metrics.exceptions_per_signal == 0.0


class TestReplayMetrics:
    """Tests for ReplayMetrics model."""

    def test_metrics_properties(self):
        """Test metrics calculated properties."""
        metrics = ReplayMetrics(
            replay_id="test",
            namespace="test",
            total_signals=100,
            total_evaluations=100,
            pass_count=80,
            fail_count=20,
        )

        assert metrics.overall_pass_rate == 80.0
        assert metrics.overall_fail_rate == 20.0


class TestGenerateMetricsReport:
    """Tests for report generation."""

    def test_generate_report(self):
        """Test generating a metrics report."""
        metrics = ReplayMetrics(
            replay_id="report_test",
            namespace="test_namespace",
            from_date=datetime(2025, 1, 1),
            to_date=datetime(2025, 1, 31),
            days_covered=30,
            total_signals=100,
            total_evaluations=100,
            total_exceptions=15,
            pass_count=85,
            fail_count=15,
            overall_pass_rate=85.0,
            overall_fail_rate=15.0,
        )

        report = generate_metrics_report(metrics)

        assert "REPLAY METRICS REPORT" in report
        assert "test_namespace" in report
        assert "100" in report
        assert "85.0%" in report

    def test_report_with_severity_breakdown(self):
        """Test report includes severity breakdown."""
        metrics = ReplayMetrics(
            replay_id="test",
            namespace="test",
            exceptions_by_severity={
                "high": 5,
                "medium": 8,
                "low": 2,
            },
        )

        report = generate_metrics_report(metrics)

        assert "SEVERITY" in report
        assert "high" in report
