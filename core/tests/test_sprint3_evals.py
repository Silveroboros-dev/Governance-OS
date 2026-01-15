"""
Sprint 3: Evaluator Tests

Tests for the extraction, regression, and policy draft evaluators.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock

import sys
sys.path.insert(0, '/Users/rk/Desktop/Governance-OS')

from evals.extraction.evaluator import (
    ExtractionEvaluator,
    ExtractionMatch,
    ExtractionEvalResult,
    ExtractionEvalSummary,
)
from evals.regression.evaluator import (
    RegressionEvaluator,
    ReplayMismatch,
    ReplayResult,
    RegressionEvalResult,
)
from evals.policy_draft.evaluator import (
    PolicyDraftEvaluator,
    RuleValidation,
    ScenarioValidation,
    PolicyDraftEvalResult,
    PolicyDraftEvalSummary,
)


class TestExtractionEvaluator:
    """Test ExtractionEvaluator."""

    def test_init_default(self):
        """Test default initialization."""
        evaluator = ExtractionEvaluator()
        assert evaluator.precision_threshold == 0.85
        assert evaluator.recall_threshold == 0.80
        assert evaluator.calibration_threshold == 0.10

    def test_init_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        evaluator = ExtractionEvaluator(
            precision_threshold=0.90,
            recall_threshold=0.85,
            calibration_threshold=0.05,
        )
        assert evaluator.precision_threshold == 0.90
        assert evaluator.recall_threshold == 0.85

    def test_load_dataset(self, tmp_path):
        """Test loading extraction dataset."""
        # Create a test dataset file
        dataset = {
            "documents": [
                {
                    "id": "doc_1",
                    "content": "Test document content",
                    "expected_signals": [
                        {"signal_type": "position_limit_breach", "payload": {}}
                    ]
                }
            ]
        }
        filepath = tmp_path / "treasury_extraction.json"
        with open(filepath, "w") as f:
            json.dump(dataset, f)

        evaluator = ExtractionEvaluator(datasets_path=tmp_path)
        loaded = evaluator.load_dataset("treasury")

        assert len(loaded) == 1
        assert loaded[0]["id"] == "doc_1"

    def test_load_dataset_missing(self, tmp_path):
        """Test loading non-existent dataset."""
        evaluator = ExtractionEvaluator(datasets_path=tmp_path)
        loaded = evaluator.load_dataset("nonexistent")
        assert loaded == []

    def test_match_signals_perfect(self):
        """Test matching signals with perfect extraction."""
        evaluator = ExtractionEvaluator()

        expected = [
            {"signal_type": "position_limit_breach", "payload": {}},
            {"signal_type": "credit_rating_change", "payload": {}},
        ]
        extracted = [
            {"signal_type": "position_limit_breach", "confidence": 0.9},
            {"signal_type": "credit_rating_change", "confidence": 0.85},
        ]

        tp, fp, fn, matches = evaluator._match_signals(expected, extracted)

        assert tp == 2  # Both matched
        assert fp == 0  # No extras
        assert fn == 0  # None missed
        assert len(matches) == 2

    def test_match_signals_with_misses(self):
        """Test matching signals with missed extractions."""
        evaluator = ExtractionEvaluator()

        expected = [
            {"signal_type": "position_limit_breach", "payload": {}},
            {"signal_type": "credit_rating_change", "payload": {}},
        ]
        extracted = [
            {"signal_type": "position_limit_breach", "confidence": 0.9},
            # Missing credit_rating_change
        ]

        tp, fp, fn, matches = evaluator._match_signals(expected, extracted)

        assert tp == 1  # One matched
        assert fp == 0  # No extras
        assert fn == 1  # One missed
        assert len([m for m in matches if not m.matched]) == 1

    def test_match_signals_with_extras(self):
        """Test matching signals with extra extractions."""
        evaluator = ExtractionEvaluator()

        expected = [
            {"signal_type": "position_limit_breach", "payload": {}},
        ]
        extracted = [
            {"signal_type": "position_limit_breach", "confidence": 0.9},
            {"signal_type": "extra_signal", "confidence": 0.5},  # Extra
        ]

        tp, fp, fn, matches = evaluator._match_signals(expected, extracted)

        assert tp == 1  # One matched
        assert fp == 1  # One extra
        assert fn == 0  # None missed

    def test_evaluate_document(self):
        """Test evaluating a single document."""
        evaluator = ExtractionEvaluator()

        document = {
            "id": "doc_1",
            "source": "email",
            "expected_signals": [
                {"signal_type": "position_limit_breach"},
                {"signal_type": "credit_rating_change"},
            ]
        }
        extracted = [
            {"signal_type": "position_limit_breach", "confidence": 0.9},
            {"signal_type": "credit_rating_change", "confidence": 0.85},
        ]

        result = evaluator.evaluate_document(document, extracted)

        assert result.document_id == "doc_1"
        assert result.precision == 1.0  # 2/2
        assert result.recall == 1.0  # 2/2
        assert result.f1_score == 1.0

    def test_evaluate_document_low_recall(self):
        """Test evaluation with low recall."""
        evaluator = ExtractionEvaluator()

        document = {
            "id": "doc_1",
            "source": "email",
            "expected_signals": [
                {"signal_type": "type_a"},
                {"signal_type": "type_b"},
                {"signal_type": "type_c"},
                {"signal_type": "type_d"},
            ]
        }
        extracted = [
            {"signal_type": "type_a", "confidence": 0.9},
            # Missing 3 signals
        ]

        result = evaluator.evaluate_document(document, extracted)

        assert result.precision == 1.0  # 1/1
        assert result.recall == 0.25  # 1/4
        assert result.false_negative == 3


class TestExtractionEvalSummary:
    """Test ExtractionEvalSummary."""

    def test_passed_above_threshold(self):
        """Test summary passes when above thresholds."""
        summary = ExtractionEvalSummary(
            precision_threshold=0.85,
            recall_threshold=0.80,
            calibration_threshold=0.10,
            avg_precision=0.90,
            avg_recall=0.85,
            avg_calibration_error=0.05,
        )
        assert summary.passed is True

    def test_failed_below_precision(self):
        """Test summary fails when below precision threshold."""
        summary = ExtractionEvalSummary(
            precision_threshold=0.85,
            recall_threshold=0.80,
            calibration_threshold=0.10,
            avg_precision=0.80,  # Below threshold
            avg_recall=0.85,
            avg_calibration_error=0.05,
        )
        assert summary.passed is False

    def test_failed_below_recall(self):
        """Test summary fails when below recall threshold."""
        summary = ExtractionEvalSummary(
            precision_threshold=0.85,
            recall_threshold=0.80,
            calibration_threshold=0.10,
            avg_precision=0.90,
            avg_recall=0.70,  # Below threshold
            avg_calibration_error=0.05,
        )
        assert summary.passed is False


class TestRegressionEvaluator:
    """Test RegressionEvaluator."""

    def test_init_default(self):
        """Test default initialization."""
        evaluator = RegressionEvaluator()
        assert evaluator.datasets_path is not None

    def test_load_historical_pack(self, tmp_path):
        """Test loading historical decisions."""
        dataset = {
            "decisions": [
                {
                    "decision_id": "DEC-001",
                    "evaluation_result": "pass",
                    "signals": [],
                }
            ]
        }
        filepath = tmp_path / "treasury_historical.json"
        with open(filepath, "w") as f:
            json.dump(dataset, f)

        evaluator = RegressionEvaluator(datasets_path=tmp_path)
        loaded = evaluator.load_historical_pack("treasury")

        assert len(loaded) == 1
        assert loaded[0]["decision_id"] == "DEC-001"

    def test_compare_results_match(self):
        """Test comparing matching results."""
        evaluator = RegressionEvaluator()

        original = {
            "evaluation_result": "pass",
            "input_hash": "abc123",
        }
        replayed = {
            "evaluation_result": "pass",
            "input_hash": "abc123",
        }

        mismatches = evaluator._compare_results(original, replayed, "DEC-001")
        assert len(mismatches) == 0

    def test_compare_results_mismatch(self):
        """Test comparing mismatching results."""
        evaluator = RegressionEvaluator()

        original = {
            "evaluation_result": "pass",
            "input_hash": "abc123",
        }
        replayed = {
            "evaluation_result": "exception_raised",  # Different
            "input_hash": "abc123",
        }

        mismatches = evaluator._compare_results(original, replayed, "DEC-001")
        assert len(mismatches) == 1
        assert mismatches[0].field == "evaluation_result"

    def test_compare_results_exception_severity(self):
        """Test comparing exception severities."""
        evaluator = RegressionEvaluator()

        original = {
            "evaluation_result": "exception_raised",
            "exception": {"severity": "high", "options": [{"id": "1"}, {"id": "2"}]},
        }
        replayed = {
            "evaluation_result": "exception_raised",
            "exception": {"severity": "medium", "options": [{"id": "1"}]},  # Different
        }

        mismatches = evaluator._compare_results(original, replayed, "DEC-001")

        # Should have severity mismatch and option count mismatch
        assert len(mismatches) >= 2
        fields = [m.field for m in mismatches]
        assert "exception.severity" in fields
        assert "exception.options.count" in fields

    def test_replay_decision_success(self):
        """Test replaying a decision successfully."""
        evaluator = RegressionEvaluator()

        historical = {
            "decision_id": "DEC-001",
            "signals": [{"type": "test"}],
            "policy_version_id": "pol_v1",
            "evaluation_result": "pass",
        }

        def mock_evaluator(signals, policy_version_id):
            return {"evaluation_result": "pass"}

        result = evaluator.replay_decision(historical, mock_evaluator)

        assert result.decision_id == "DEC-001"
        assert result.matched is True
        assert result.original_result == "pass"
        assert result.replayed_result == "pass"

    def test_replay_decision_drift(self):
        """Test detecting drift in replayed decision."""
        evaluator = RegressionEvaluator()

        historical = {
            "decision_id": "DEC-001",
            "signals": [{"type": "test"}],
            "policy_version_id": "pol_v1",
            "evaluation_result": "pass",
        }

        def mock_evaluator(signals, policy_version_id):
            return {"evaluation_result": "exception_raised"}  # Different!

        result = evaluator.replay_decision(historical, mock_evaluator)

        assert result.decision_id == "DEC-001"
        assert result.matched is False
        assert len(result.mismatches) > 0

    def test_replay_decision_error(self):
        """Test handling errors during replay."""
        evaluator = RegressionEvaluator()

        historical = {
            "decision_id": "DEC-001",
            "signals": [],
            "policy_version_id": "pol_v1",
            "evaluation_result": "pass",
        }

        def mock_evaluator(signals, policy_version_id):
            raise ValueError("Test error")

        result = evaluator.replay_decision(historical, mock_evaluator)

        assert result.matched is False
        assert result.replayed_result == "error"
        assert "Test error" in result.error


class TestRegressionEvalResult:
    """Test RegressionEvalResult."""

    def test_drift_detected_true(self):
        """Test drift detection when mismatches exist."""
        result = RegressionEvalResult(
            mismatch_count=2,
            matching_count=8,
        )
        assert result.drift_detected is True

    def test_drift_detected_false(self):
        """Test no drift when no mismatches."""
        result = RegressionEvalResult(
            mismatch_count=0,
            matching_count=10,
        )
        assert result.drift_detected is False

    def test_passed_with_no_drift_no_errors(self):
        """Test passing when no drift and no errors."""
        result = RegressionEvalResult(
            mismatch_count=0,
            error_count=0,
            matching_count=10,
        )
        assert result.passed is True

    def test_failed_with_errors(self):
        """Test failing when errors exist."""
        result = RegressionEvalResult(
            mismatch_count=0,
            error_count=1,
            matching_count=9,
        )
        assert result.passed is False


class TestPolicyDraftEvaluator:
    """Test PolicyDraftEvaluator."""

    def test_init_default(self):
        """Test default initialization."""
        evaluator = PolicyDraftEvaluator()
        assert evaluator.schema_threshold == 1.0
        assert evaluator.rule_threshold == 0.90
        assert evaluator.scenario_threshold == 0.80

    def test_load_dataset(self, tmp_path):
        """Test loading policy prompts dataset."""
        dataset = {
            "prompts": [
                {
                    "id": "prompt_1",
                    "description": "Create a position limit policy",
                    "pack": "treasury",
                }
            ]
        }
        filepath = tmp_path / "treasury_policy_prompts.json"
        with open(filepath, "w") as f:
            json.dump(dataset, f)

        evaluator = PolicyDraftEvaluator(datasets_path=tmp_path)
        loaded = evaluator.load_dataset("treasury")

        assert len(loaded) == 1
        assert loaded[0]["id"] == "prompt_1"

    def test_validate_rule_valid(self):
        """Test validating a valid rule."""
        evaluator = PolicyDraftEvaluator()

        rule = {
            "id": "rule_1",
            "condition": "IF position > limit THEN raise_exception",
            "action": "raise_exception",
            "severity": "high",
        }

        result = evaluator._validate_rule(rule, 0)

        assert result.rule_id == "rule_1"
        assert result.has_condition is True
        assert result.has_action is True
        assert result.has_severity is True
        assert result.condition_parseable is True

    def test_validate_rule_missing_fields(self):
        """Test validating a rule with missing fields."""
        evaluator = PolicyDraftEvaluator()

        rule = {
            "id": "rule_1",
            "condition": "IF position > limit",
            # Missing action and severity
        }

        result = evaluator._validate_rule(rule, 0)

        assert result.has_condition is True
        assert result.has_action is False
        assert result.has_severity is False
        assert result.notes is not None

    def test_validate_scenario_valid(self):
        """Test validating a valid test scenario."""
        evaluator = PolicyDraftEvaluator()

        scenario = {
            "description": "Test position exceeds limit",
            "signals": [{"type": "position_limit_breach", "value": 120}],
            "expected_result": "exception_raised",
        }

        result = evaluator._validate_scenario(scenario, 0, ["rule_1"])

        assert result.has_description is True
        assert result.has_signals is True
        assert result.has_expected_result is True

    def test_validate_scenario_missing_signals(self):
        """Test validating scenario with no signals."""
        evaluator = PolicyDraftEvaluator()

        scenario = {
            "description": "Test scenario",
            "signals": [],  # Empty
            "expected_result": "pass",
        }

        result = evaluator._validate_scenario(scenario, 0, ["rule_1"])

        assert result.has_signals is False
        assert result.notes is not None

    def test_evaluate_draft_complete(self):
        """Test evaluating a complete policy draft."""
        evaluator = PolicyDraftEvaluator()

        prompt = {"id": "prompt_1", "pack": "treasury"}
        draft_output = {
            "name": "Position Limit Policy",
            "description": "Monitors position limit breaches",
            "rules": [
                {
                    "id": "rule_1",
                    "condition": "IF position > limit THEN raise",
                    "action": "raise_exception",
                    "severity": "high",
                }
            ],
            "test_scenarios": [
                {
                    "description": "Position exceeds limit",
                    "signals": [{"type": "test"}],
                    "expected_result": "exception",
                }
            ],
        }

        result = evaluator.evaluate_draft(prompt, draft_output)

        assert result.prompt_id == "prompt_1"
        assert result.has_name is True
        assert result.has_description is True
        assert result.has_rules is True
        assert result.rule_count == 1
        assert result.scenario_count == 1
        assert result.valid_rules == 1
        assert result.schema_score == 1.0

    def test_evaluate_draft_incomplete(self):
        """Test evaluating an incomplete policy draft."""
        evaluator = PolicyDraftEvaluator()

        prompt = {"id": "prompt_1", "pack": "treasury"}
        draft_output = {
            # Missing name
            "description": "Test policy",
            "rules": [],  # Empty rules
            "test_scenarios": [],
        }

        result = evaluator.evaluate_draft(prompt, draft_output)

        assert result.has_name is False
        assert result.has_rules is False
        assert result.schema_score < 1.0


class TestPolicyDraftEvalSummary:
    """Test PolicyDraftEvalSummary."""

    def test_passed_above_thresholds(self):
        """Test summary passes when above all thresholds."""
        summary = PolicyDraftEvalSummary(
            schema_threshold=1.0,
            rule_threshold=0.90,
            scenario_threshold=0.80,
            avg_schema_score=1.0,
            avg_rule_score=0.95,
            avg_scenario_score=0.85,
        )
        assert summary.passed is True

    def test_failed_below_schema_threshold(self):
        """Test summary fails when below schema threshold."""
        summary = PolicyDraftEvalSummary(
            schema_threshold=1.0,
            rule_threshold=0.90,
            scenario_threshold=0.80,
            avg_schema_score=0.90,  # Below 1.0 threshold
            avg_rule_score=0.95,
            avg_scenario_score=0.85,
        )
        assert summary.passed is False

    def test_failed_below_rule_threshold(self):
        """Test summary fails when below rule threshold."""
        summary = PolicyDraftEvalSummary(
            schema_threshold=1.0,
            rule_threshold=0.90,
            scenario_threshold=0.80,
            avg_schema_score=1.0,
            avg_rule_score=0.80,  # Below 0.90 threshold
            avg_scenario_score=0.85,
        )
        assert summary.passed is False
