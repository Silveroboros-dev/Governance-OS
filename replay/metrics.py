"""
Metrics Module - Exception budgets and replay statistics.

Provides metrics for monitoring exception rates, policy effectiveness,
and replay performance.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .harness import ReplayResult


class ExceptionBudget(BaseModel):
    """Budget configuration for exception rates."""

    policy_id: Optional[str] = None  # None means all policies
    severity: Optional[str] = None  # None means all severities
    max_exceptions_per_day: int = 10
    max_exceptions_per_week: int = 50
    warning_threshold_percent: float = 80.0


class BudgetStatus(BaseModel):
    """Current status of an exception budget."""

    budget: ExceptionBudget
    period: str  # "day" or "week"
    current_count: int
    max_allowed: int
    utilization_percent: float
    is_exceeded: bool
    is_warning: bool

    @property
    def remaining(self) -> int:
        return max(0, self.max_allowed - self.current_count)


class PolicyMetrics(BaseModel):
    """Metrics for a single policy."""

    policy_id: str
    policy_name: str

    # Evaluation counts
    total_evaluations: int = 0
    pass_count: int = 0
    fail_count: int = 0
    inconclusive_count: int = 0

    # Rates
    pass_rate: float = 0.0
    fail_rate: float = 0.0

    # Exception metrics
    exceptions_raised: int = 0
    exceptions_by_severity: Dict[str, int] = Field(default_factory=dict)

    # Time-based metrics
    avg_evaluations_per_day: float = 0.0
    avg_exceptions_per_day: float = 0.0


class ReplayMetrics(BaseModel):
    """Aggregate metrics for a replay run."""

    replay_id: str
    namespace: str
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    # Time range
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    days_covered: int = 0

    # Overall counts
    total_signals: int = 0
    total_evaluations: int = 0
    total_exceptions: int = 0

    # By result
    pass_count: int = 0
    fail_count: int = 0
    inconclusive_count: int = 0

    # Rates (computed automatically)
    _overall_pass_rate: float = 0.0
    _overall_fail_rate: float = 0.0
    _exceptions_per_signal: float = 0.0

    @property
    def overall_pass_rate(self) -> float:
        """Calculate pass rate from counts."""
        if self.total_evaluations == 0:
            return 0.0
        return (self.pass_count / self.total_evaluations) * 100

    @property
    def overall_fail_rate(self) -> float:
        """Calculate fail rate from counts."""
        if self.total_evaluations == 0:
            return 0.0
        return (self.fail_count / self.total_evaluations) * 100

    @property
    def exceptions_per_signal(self) -> float:
        """Calculate exceptions per signal ratio."""
        if self.total_signals == 0:
            return 0.0
        return self.total_exceptions / self.total_signals

    # By severity
    exceptions_by_severity: Dict[str, int] = Field(default_factory=dict)

    # By policy
    policy_metrics: List[PolicyMetrics] = Field(default_factory=list)

    # Budget status
    budget_statuses: List[BudgetStatus] = Field(default_factory=list)


class MetricsCalculator:
    """Calculates metrics from replay results."""

    def __init__(self, budgets: Optional[List[ExceptionBudget]] = None):
        """
        Initialize with optional budget configurations.

        Args:
            budgets: List of exception budgets to track
        """
        self.budgets = budgets or []

    def calculate(self, result: ReplayResult) -> ReplayMetrics:
        """
        Calculate metrics from a replay result.

        Args:
            result: ReplayResult to analyze

        Returns:
            ReplayMetrics with computed statistics
        """
        # Handle optional config
        from_date = result.config.from_date if result.config else None
        to_date = result.config.to_date if result.config else None

        metrics = ReplayMetrics(
            replay_id=result.replay_id,
            namespace=result.namespace,
            from_date=from_date,
            to_date=to_date
        )

        # Calculate days covered
        if from_date and to_date:
            delta = to_date - from_date
            metrics.days_covered = max(1, delta.days)
        elif result.evaluations:
            timestamps = [e.evaluated_at for e in result.evaluations]
            delta = max(timestamps) - min(timestamps)
            metrics.days_covered = max(1, delta.days)
        else:
            metrics.days_covered = 1

        # Overall counts
        metrics.total_signals = result.signals_processed
        metrics.total_evaluations = len(result.evaluations)
        metrics.total_exceptions = len(result.exceptions_raised)

        metrics.pass_count = result.pass_count
        metrics.fail_count = result.fail_count
        metrics.inconclusive_count = result.inconclusive_count

        # Rates are computed via @property - no need to set them

        # By severity
        for exc in result.exceptions_raised:
            severity = exc.severity
            metrics.exceptions_by_severity[severity] = metrics.exceptions_by_severity.get(severity, 0) + 1

        # By policy
        metrics.policy_metrics = self._calculate_policy_metrics(result, metrics.days_covered)

        # Budget status
        metrics.budget_statuses = self._check_budgets(result, metrics.days_covered)

        return metrics

    def _calculate_policy_metrics(
        self,
        result: ReplayResult,
        days: int
    ) -> List[PolicyMetrics]:
        """Calculate per-policy metrics."""
        policy_data: Dict[str, Dict[str, Any]] = {}

        # Aggregate evaluations by policy
        for eval in result.evaluations:
            if eval.policy_id not in policy_data:
                policy_data[eval.policy_id] = {
                    "total": 0,
                    "pass": 0,
                    "fail": 0,
                    "inconclusive": 0,
                    "exceptions": 0,
                    "exceptions_by_severity": {}
                }

            data = policy_data[eval.policy_id]
            data["total"] += 1

            if eval.result == "pass":
                data["pass"] += 1
            elif eval.result == "fail":
                data["fail"] += 1
            else:
                data["inconclusive"] += 1

        # Count exceptions by policy
        for exc in result.exceptions_raised:
            if exc.policy_id in policy_data:
                policy_data[exc.policy_id]["exceptions"] += 1
                severity = exc.severity
                exc_by_sev = policy_data[exc.policy_id]["exceptions_by_severity"]
                exc_by_sev[severity] = exc_by_sev.get(severity, 0) + 1

        # Build PolicyMetrics objects
        metrics = []
        for policy_id, data in policy_data.items():
            pm = PolicyMetrics(
                policy_id=policy_id,
                policy_name=policy_id,  # Could look up actual name
                total_evaluations=data["total"],
                pass_count=data["pass"],
                fail_count=data["fail"],
                inconclusive_count=data["inconclusive"],
                exceptions_raised=data["exceptions"],
                exceptions_by_severity=data["exceptions_by_severity"]
            )

            if pm.total_evaluations > 0:
                pm.pass_rate = (pm.pass_count / pm.total_evaluations) * 100
                pm.fail_rate = (pm.fail_count / pm.total_evaluations) * 100

            if days > 0:
                pm.avg_evaluations_per_day = pm.total_evaluations / days
                pm.avg_exceptions_per_day = pm.exceptions_raised / days

            metrics.append(pm)

        return metrics

    def _check_budgets(
        self,
        result: ReplayResult,
        days: int
    ) -> List[BudgetStatus]:
        """Check exception budgets against replay results."""
        statuses = []

        for budget in self.budgets:
            # Filter exceptions for this budget
            matching_exceptions = [
                exc for exc in result.exceptions_raised
                if (budget.policy_id is None or exc.policy_id == budget.policy_id)
                and (budget.severity is None or exc.severity == budget.severity)
            ]

            count = len(matching_exceptions)

            # Daily budget
            daily_avg = count / max(1, days)
            daily_max = budget.max_exceptions_per_day
            daily_utilization = (daily_avg / daily_max) * 100 if daily_max > 0 else 0

            statuses.append(BudgetStatus(
                budget=budget,
                period="day",
                current_count=int(daily_avg),
                max_allowed=daily_max,
                utilization_percent=daily_utilization,
                is_exceeded=daily_avg > daily_max,
                is_warning=daily_utilization >= budget.warning_threshold_percent
            ))

            # Weekly budget (assuming 7 days)
            weekly_avg = (count / max(1, days)) * 7
            weekly_max = budget.max_exceptions_per_week
            weekly_utilization = (weekly_avg / weekly_max) * 100 if weekly_max > 0 else 0

            statuses.append(BudgetStatus(
                budget=budget,
                period="week",
                current_count=int(weekly_avg),
                max_allowed=weekly_max,
                utilization_percent=weekly_utilization,
                is_exceeded=weekly_avg > weekly_max,
                is_warning=weekly_utilization >= budget.warning_threshold_percent
            ))

        return statuses


def generate_metrics_report(metrics: ReplayMetrics) -> str:
    """
    Generate a human-readable metrics report.

    Args:
        metrics: ReplayMetrics to report on

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 60,
        "REPLAY METRICS REPORT",
        "=" * 60,
        "",
        f"Replay ID: {metrics.replay_id[:8]}...",
        f"Namespace: {metrics.namespace}",
        f"Computed at: {metrics.computed_at.isoformat()}",
        "",
    ]

    if metrics.from_date and metrics.to_date:
        lines.append(f"Period: {metrics.from_date.date()} to {metrics.to_date.date()} ({metrics.days_covered} days)")

    lines.extend([
        "",
        "-" * 40,
        "OVERALL METRICS",
        "-" * 40,
        f"Signals processed: {metrics.total_signals}",
        f"Evaluations: {metrics.total_evaluations}",
        f"Exceptions raised: {metrics.total_exceptions}",
        "",
        f"Pass rate: {metrics.overall_pass_rate:.1f}%",
        f"Fail rate: {metrics.overall_fail_rate:.1f}%",
        f"Exceptions per signal: {metrics.exceptions_per_signal:.2f}",
    ])

    if metrics.exceptions_by_severity:
        lines.extend([
            "",
            "-" * 40,
            "EXCEPTIONS BY SEVERITY",
            "-" * 40,
        ])
        for severity, count in sorted(metrics.exceptions_by_severity.items()):
            lines.append(f"  {severity}: {count}")

    if metrics.policy_metrics:
        lines.extend([
            "",
            "-" * 40,
            "TOP POLICIES BY EXCEPTION RATE",
            "-" * 40,
        ])
        sorted_policies = sorted(
            metrics.policy_metrics,
            key=lambda p: p.fail_rate,
            reverse=True
        )[:5]
        for pm in sorted_policies:
            lines.append(f"  {pm.policy_id[:20]}: {pm.fail_rate:.1f}% fail rate ({pm.exceptions_raised} exceptions)")

    if metrics.budget_statuses:
        exceeded = [s for s in metrics.budget_statuses if s.is_exceeded]
        warnings = [s for s in metrics.budget_statuses if s.is_warning and not s.is_exceeded]

        if exceeded:
            lines.extend([
                "",
                "-" * 40,
                "BUDGET EXCEEDED",
                "-" * 40,
            ])
            for status in exceeded:
                lines.append(f"  {status.period}: {status.current_count}/{status.max_allowed} ({status.utilization_percent:.0f}%)")

        if warnings:
            lines.extend([
                "",
                "-" * 40,
                "BUDGET WARNINGS",
                "-" * 40,
            ])
            for status in warnings:
                lines.append(f"  {status.period}: {status.current_count}/{status.max_allowed} ({status.utilization_percent:.0f}%)")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
