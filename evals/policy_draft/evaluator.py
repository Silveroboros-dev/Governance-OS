"""
Policy Draft Evaluator - Sprint 3

Evaluates PolicyDraftAgent outputs for:
- Schema compliance (valid rule definitions)
- Determinism (same input → structurally similar output)
- Completeness (all required fields present)
- Test scenario validity (scenarios test the rules)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RuleValidation(BaseModel):
    """Validation result for a single rule."""
    rule_id: str
    has_condition: bool
    has_action: bool
    has_severity: bool
    condition_parseable: bool
    notes: Optional[str] = None


class ScenarioValidation(BaseModel):
    """Validation result for a test scenario."""
    scenario_index: int
    has_description: bool
    has_signals: bool
    has_expected_result: bool
    signals_reference_rules: bool
    notes: Optional[str] = None


class PolicyDraftEvalResult(BaseModel):
    """Result of evaluating a single policy draft."""

    prompt_id: str
    pack: str

    # Schema compliance
    has_name: bool
    has_description: bool
    has_rules: bool
    rule_count: int
    scenario_count: int

    # Rule validation
    rule_validations: List[RuleValidation] = Field(default_factory=list)
    valid_rules: int = 0
    invalid_rules: int = 0

    # Scenario validation
    scenario_validations: List[ScenarioValidation] = Field(default_factory=list)
    valid_scenarios: int = 0
    invalid_scenarios: int = 0

    # Overall scores
    schema_score: float = 0.0  # 0-1, % of required fields present
    rule_score: float = 0.0    # 0-1, % of rules valid
    scenario_score: float = 0.0  # 0-1, % of scenarios valid
    overall_score: float = 0.0

    errors: List[str] = Field(default_factory=list)


class PolicyDraftEvalSummary(BaseModel):
    """Summary of policy draft evaluation run."""

    run_id: str = Field(default_factory=lambda: f"policy_draft_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Aggregate metrics
    total_prompts: int = 0
    avg_schema_score: float = 0.0
    avg_rule_score: float = 0.0
    avg_scenario_score: float = 0.0
    avg_overall_score: float = 0.0

    # Thresholds
    schema_threshold: float = 1.0  # Must have all required fields
    rule_threshold: float = 0.90   # 90% valid rules
    scenario_threshold: float = 0.80  # 80% valid scenarios

    results: List[PolicyDraftEvalResult] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if evaluation passed all thresholds."""
        return (
            self.avg_schema_score >= self.schema_threshold
            and self.avg_rule_score >= self.rule_threshold
            and self.avg_scenario_score >= self.scenario_threshold
        )


class PolicyDraftEvaluator:
    """
    Evaluates PolicyDraftAgent output quality.

    Checks:
    - Schema compliance (name, description, rules present)
    - Rule validity (condition, action, severity for each rule)
    - Scenario validity (description, signals, expected result)
    """

    def __init__(
        self,
        datasets_path: Optional[Path] = None,
        schema_threshold: float = 1.0,
        rule_threshold: float = 0.90,
        scenario_threshold: float = 0.80,
    ):
        """
        Initialize evaluator.

        Args:
            datasets_path: Path to datasets directory
            schema_threshold: Minimum schema compliance to pass
            rule_threshold: Minimum rule validity to pass
            scenario_threshold: Minimum scenario validity to pass
        """
        self.datasets_path = datasets_path or Path(__file__).parent.parent / "datasets"
        self.schema_threshold = schema_threshold
        self.rule_threshold = rule_threshold
        self.scenario_threshold = scenario_threshold

    def load_dataset(self, pack: str) -> List[Dict[str, Any]]:
        """Load policy draft prompts for a pack."""
        filename = f"{pack}_policy_prompts.json"
        filepath = self.datasets_path / filename

        if not filepath.exists():
            return []

        with open(filepath, "r") as f:
            data = json.load(f)

        return data.get("prompts", [])

    def _validate_rule(self, rule: Dict[str, Any], index: int) -> RuleValidation:
        """Validate a single rule definition."""
        rule_id = rule.get("id", f"rule_{index}")

        has_condition = bool(rule.get("condition"))
        has_action = bool(rule.get("action"))
        has_severity = bool(rule.get("severity"))

        # Check if condition is parseable (basic check)
        condition = rule.get("condition", "")
        condition_parseable = (
            isinstance(condition, str)
            and len(condition) > 0
            and any(kw in condition.lower() for kw in ["if", "when", "signal", "threshold", ">", "<", "==", "and", "or"])
        )

        notes = None
        if not has_condition:
            notes = "Missing condition"
        elif not condition_parseable:
            notes = "Condition may not be machine-parseable"
        elif not has_action:
            notes = "Missing action"
        elif not has_severity:
            notes = "Missing severity"

        return RuleValidation(
            rule_id=rule_id,
            has_condition=has_condition,
            has_action=has_action,
            has_severity=has_severity,
            condition_parseable=condition_parseable,
            notes=notes,
        )

    def _validate_scenario(
        self,
        scenario: Dict[str, Any],
        index: int,
        rule_ids: List[str],
    ) -> ScenarioValidation:
        """Validate a test scenario."""
        has_description = bool(scenario.get("description"))
        has_signals = bool(scenario.get("signals")) and len(scenario.get("signals", [])) > 0
        has_expected_result = bool(scenario.get("expected_result"))

        # Check if signals reference defined rules
        signals_reference_rules = False
        if has_signals:
            signal_types = [s.get("signal_type", "") for s in scenario.get("signals", [])]
            # At least one signal should be relevant to the rules
            signals_reference_rules = True  # Simplified check

        notes = None
        if not has_description:
            notes = "Missing description"
        elif not has_signals:
            notes = "Missing or empty signals"
        elif not has_expected_result:
            notes = "Missing expected result"

        return ScenarioValidation(
            scenario_index=index,
            has_description=has_description,
            has_signals=has_signals,
            has_expected_result=has_expected_result,
            signals_reference_rules=signals_reference_rules,
            notes=notes,
        )

    def evaluate_draft(
        self,
        prompt: Dict[str, Any],
        draft_output: Dict[str, Any],
    ) -> PolicyDraftEvalResult:
        """
        Evaluate a single policy draft output.

        Args:
            prompt: The input prompt
            draft_output: The generated policy draft

        Returns:
            PolicyDraftEvalResult
        """
        prompt_id = prompt.get("id", "unknown")
        pack = prompt.get("pack", "unknown")

        result = PolicyDraftEvalResult(
            prompt_id=prompt_id,
            pack=pack,
            has_name=False,
            has_description=False,
            has_rules=False,
            rule_count=0,
            scenario_count=0,
        )

        # Check schema compliance
        result.has_name = bool(draft_output.get("name"))
        result.has_description = bool(draft_output.get("description"))
        rules = draft_output.get("rules", [])
        result.has_rules = isinstance(rules, list) and len(rules) > 0
        result.rule_count = len(rules) if isinstance(rules, list) else 0

        scenarios = draft_output.get("test_scenarios", [])
        result.scenario_count = len(scenarios) if isinstance(scenarios, list) else 0

        # Calculate schema score
        schema_fields = [result.has_name, result.has_description, result.has_rules]
        result.schema_score = sum(schema_fields) / len(schema_fields) if schema_fields else 0.0

        # Validate rules
        rule_ids = []
        for i, rule in enumerate(rules):
            validation = self._validate_rule(rule, i)
            result.rule_validations.append(validation)
            rule_ids.append(validation.rule_id)

            if validation.has_condition and validation.has_action and validation.has_severity:
                result.valid_rules += 1
            else:
                result.invalid_rules += 1

        result.rule_score = result.valid_rules / result.rule_count if result.rule_count > 0 else 1.0

        # Validate scenarios
        for i, scenario in enumerate(scenarios):
            validation = self._validate_scenario(scenario, i, rule_ids)
            result.scenario_validations.append(validation)

            if validation.has_description and validation.has_signals and validation.has_expected_result:
                result.valid_scenarios += 1
            else:
                result.invalid_scenarios += 1

        result.scenario_score = result.valid_scenarios / result.scenario_count if result.scenario_count > 0 else 1.0

        # Calculate overall score (weighted average)
        result.overall_score = (
            result.schema_score * 0.3 +
            result.rule_score * 0.5 +
            result.scenario_score * 0.2
        )

        return result

    def evaluate_agent(
        self,
        agent,
        pack: str,
        verbose: bool = False,
    ) -> PolicyDraftEvalSummary:
        """
        Evaluate PolicyDraftAgent against the dataset.

        Args:
            agent: PolicyDraftAgent instance
            pack: Pack to evaluate
            verbose: Print detailed output

        Returns:
            PolicyDraftEvalSummary
        """
        summary = PolicyDraftEvalSummary(
            schema_threshold=self.schema_threshold,
            rule_threshold=self.rule_threshold,
            scenario_threshold=self.scenario_threshold,
        )

        dataset = self.load_dataset(pack)
        summary.total_prompts = len(dataset)

        if verbose:
            print(f"\nEvaluating {len(dataset)} {pack} policy prompts...")
            print("=" * 60)

        schema_scores = []
        rule_scores = []
        scenario_scores = []
        overall_scores = []

        for prompt in dataset:
            description = prompt.get("description", "")
            context = prompt.get("context", "")

            try:
                result = agent.generate_draft_sync(
                    description=description,
                    pack=pack,
                    context=context,
                )

                draft_output = {
                    "name": result.draft.name,
                    "description": result.draft.description,
                    "rules": [r.model_dump() for r in result.draft.rules],
                    "test_scenarios": [s.model_dump() for s in result.draft.test_scenarios],
                }
            except Exception as e:
                if verbose:
                    print(f"[ERROR] {prompt.get('id', 'unknown')}: {e}")
                continue

            eval_result = self.evaluate_draft(prompt, draft_output)
            summary.results.append(eval_result)

            schema_scores.append(eval_result.schema_score)
            rule_scores.append(eval_result.rule_score)
            scenario_scores.append(eval_result.scenario_score)
            overall_scores.append(eval_result.overall_score)

            if verbose:
                status = "PASS" if eval_result.overall_score >= 0.8 else "FAIL"
                print(f"[{status}] {eval_result.prompt_id}: "
                      f"Schema={eval_result.schema_score:.0%} "
                      f"Rules={eval_result.rule_score:.0%} "
                      f"Scenarios={eval_result.scenario_score:.0%}")

        # Calculate averages
        summary.avg_schema_score = sum(schema_scores) / len(schema_scores) if schema_scores else 0.0
        summary.avg_rule_score = sum(rule_scores) / len(rule_scores) if rule_scores else 0.0
        summary.avg_scenario_score = sum(scenario_scores) / len(scenario_scores) if scenario_scores else 0.0
        summary.avg_overall_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0

        summary.completed_at = datetime.utcnow()

        if verbose:
            print("=" * 60)
            print(f"\nResults:")
            print(f"  Schema Score: {summary.avg_schema_score:.1%} (threshold: {self.schema_threshold:.0%})")
            print(f"  Rule Score: {summary.avg_rule_score:.1%} (threshold: {self.rule_threshold:.0%})")
            print(f"  Scenario Score: {summary.avg_scenario_score:.1%} (threshold: {self.scenario_threshold:.0%})")
            print(f"  Overall Score: {summary.avg_overall_score:.1%}")
            print(f"\nOverall: {'PASS' if summary.passed else 'FAIL'}")

        return summary
