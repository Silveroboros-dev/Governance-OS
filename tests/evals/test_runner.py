"""
Tests for Eval Runner - CI-integrated evaluation runner.
"""

import pytest
import json
from pathlib import Path

from evals.runner import (
    EvalRunner,
    EvalRunResult,
    TestCaseResult,
)


class TestEvalRunner:
    """Tests for EvalRunner class."""

    @pytest.fixture
    def runner(self):
        """Create an eval runner with default settings."""
        return EvalRunner()

    @pytest.fixture
    def custom_dataset_path(self, tmp_path):
        """Create a custom dataset directory."""
        return tmp_path

    def test_runner_initialization(self, runner):
        """Test runner initialization."""
        assert runner.strict_grounding is True
        assert runner.datasets_path.exists()

    def test_load_goldens(self, runner):
        """Test loading golden test cases."""
        cases = runner.load_goldens()

        assert len(cases) > 0
        assert all("id" in case for case in cases)
        assert all("expected_result" in case for case in cases)

    def test_load_goldens_file_not_found(self, custom_dataset_path):
        """Test error when golden file doesn't exist."""
        runner = EvalRunner(datasets_path=custom_dataset_path)

        with pytest.raises(FileNotFoundError):
            runner.load_goldens("nonexistent.json")

    def test_run_case_expected_pass(self, runner):
        """Test running a case expected to pass."""
        case = {
            "id": "test_001",
            "name": "Test Pass",
            "expected_result": "pass",
            "memo": {
                "decision_id": "dec_001",
                "title": "Test",
                "sections": [
                    {
                        "heading": "Test",
                        "claims": [
                            {
                                "text": "Valid claim",
                                "evidence_refs": [
                                    {"evidence_id": "sig_001", "evidence_type": "signal"}
                                ],
                            }
                        ],
                    }
                ],
            },
            "evidence_pack": {
                "evidence_items": [{"evidence_id": "sig_001", "type": "signal"}]
            },
        }

        result = runner.run_case(case)

        assert result.case_id == "test_001"
        assert result.passed is True
        assert result.expected_result == "pass"
        assert result.actual_result == "pass"

    def test_run_case_expected_fail_grounding(self, runner):
        """Test running a case expected to fail on grounding."""
        case = {
            "id": "test_002",
            "name": "Test Fail Grounding",
            "expected_result": "fail",
            "expected_error_type": "ungrounded_claim",
            "memo": {
                "decision_id": "dec_001",
                "title": "Test",
                "sections": [
                    {
                        "heading": "Test",
                        "claims": [
                            {
                                "text": "Ungrounded claim",
                                "evidence_refs": [],  # No evidence
                            }
                        ],
                    }
                ],
            },
            "evidence_pack": {"evidence_items": []},
        }

        result = runner.run_case(case)

        assert result.passed is True  # Expected to fail, and it did fail
        assert result.expected_result == "fail"
        assert result.actual_result == "fail"

    def test_run_case_expected_fail_hallucination(self, runner):
        """Test running a case expected to fail on hallucination."""
        case = {
            "id": "test_003",
            "name": "Test Fail Hallucination",
            "expected_result": "fail",
            "expected_error_type": "recommendation",
            "memo": {
                "decision_id": "dec_001",
                "title": "Test",
                "sections": [
                    {
                        "heading": "Test",
                        "claims": [
                            {
                                "text": "The team should consider this option",
                                "evidence_refs": [
                                    {"evidence_id": "sig_001", "evidence_type": "signal"}
                                ],
                            }
                        ],
                    }
                ],
            },
            "evidence_pack": {
                "evidence_items": [{"evidence_id": "sig_001", "type": "signal"}]
            },
        }

        result = runner.run_case(case)

        assert result.passed is True  # Expected to fail, and it did fail
        assert result.expected_result == "fail"

    def test_run_case_unexpected_pass(self, runner):
        """Test case that unexpectedly passes."""
        case = {
            "id": "test_004",
            "name": "Unexpected Pass",
            "expected_result": "fail",  # Expected to fail
            "expected_error_type": "recommendation",
            "memo": {
                "decision_id": "dec_001",
                "title": "Test",
                "sections": [
                    {
                        "heading": "Test",
                        "claims": [
                            {
                                "text": "Clean factual statement",  # No forbidden patterns
                                "evidence_refs": [
                                    {"evidence_id": "sig_001", "evidence_type": "signal"}
                                ],
                            }
                        ],
                    }
                ],
            },
            "evidence_pack": {
                "evidence_items": [{"evidence_id": "sig_001", "type": "signal"}]
            },
        }

        result = runner.run_case(case)

        assert result.passed is False  # Test case failed (unexpected result)
        assert result.expected_result == "fail"
        assert result.actual_result == "pass"

    def test_run_all(self, runner):
        """Test running all golden test cases."""
        result = runner.run_all()

        assert isinstance(result, EvalRunResult)
        assert result.total_cases > 0
        assert result.passed_cases + result.failed_cases == result.total_cases

    def test_run_all_with_verbose(self, runner, capsys):
        """Test verbose output during run_all."""
        result = runner.run_all(verbose=True)

        captured = capsys.readouterr()
        assert "Running" in captured.out
        assert "PASS" in captured.out or "FAIL" in captured.out

    def test_run_and_exit_all_pass(self, runner, monkeypatch):
        """Test run_and_exit returns 0 when all pass."""
        # Mock run_all to return all passing
        def mock_run_all(verbose=False):
            return EvalRunResult(
                total_cases=5,
                passed_cases=5,
                failed_cases=0,
            )

        monkeypatch.setattr(runner, "run_all", mock_run_all)

        exit_code = runner.run_and_exit()

        assert exit_code == 0

    def test_run_and_exit_some_fail(self, runner, monkeypatch):
        """Test run_and_exit returns 1 when some fail."""
        # Mock run_all to return some failing
        def mock_run_all(verbose=False):
            return EvalRunResult(
                total_cases=5,
                passed_cases=3,
                failed_cases=2,
            )

        monkeypatch.setattr(runner, "run_all", mock_run_all)

        exit_code = runner.run_and_exit()

        assert exit_code == 1


class TestEvalRunResult:
    """Tests for EvalRunResult model."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = EvalRunResult(
            total_cases=10,
            passed_cases=8,
            failed_cases=2,
        )

        assert result.success_rate == 80.0

    def test_success_rate_zero_cases(self):
        """Test success rate with zero cases."""
        result = EvalRunResult(
            total_cases=0,
            passed_cases=0,
            failed_cases=0,
        )

        assert result.success_rate == 100.0

    def test_all_passed_property(self):
        """Test all_passed property."""
        result_all_pass = EvalRunResult(
            total_cases=5,
            passed_cases=5,
            failed_cases=0,
        )
        assert result_all_pass.all_passed is True

        result_some_fail = EvalRunResult(
            total_cases=5,
            passed_cases=3,
            failed_cases=2,
        )
        assert result_some_fail.all_passed is False


class TestTestCaseResult:
    """Tests for TestCaseResult model."""

    def test_result_creation(self):
        """Test creating a test case result."""
        result = TestCaseResult(
            case_id="test_001",
            case_name="Test Case",
            expected_result="pass",
            actual_result="pass",
            passed=True,
            duration_ms=15.5,
        )

        assert result.case_id == "test_001"
        assert result.passed is True
        assert result.duration_ms == 15.5

    def test_result_with_error(self):
        """Test result with error message."""
        result = TestCaseResult(
            case_id="test_002",
            case_name="Failed Test",
            expected_result="pass",
            actual_result="error",
            passed=False,
            error_message="Something went wrong",
        )

        assert result.passed is False
        assert result.error_message == "Something went wrong"


class TestGoldenDatasetIntegrity:
    """Tests to verify golden dataset integrity."""

    @pytest.fixture
    def runner(self):
        return EvalRunner()

    def test_golden_dataset_valid_json(self, runner):
        """Test that golden dataset is valid JSON."""
        filepath = runner.datasets_path / "narrative_goldens.json"
        with open(filepath) as f:
            data = json.load(f)

        assert "test_cases" in data
        assert isinstance(data["test_cases"], list)

    def test_golden_cases_have_required_fields(self, runner):
        """Test that all cases have required fields."""
        cases = runner.load_goldens()

        required_fields = ["id", "name", "expected_result", "memo", "evidence_pack"]

        for case in cases:
            for field in required_fields:
                assert field in case, f"Case {case.get('id')} missing field: {field}"

    def test_golden_expected_results_valid(self, runner):
        """Test that expected results are valid values."""
        cases = runner.load_goldens()

        valid_results = ["pass", "fail"]

        for case in cases:
            assert case["expected_result"] in valid_results, \
                f"Case {case['id']} has invalid expected_result: {case['expected_result']}"

    def test_golden_fail_cases_have_error_type(self, runner):
        """Test that fail cases specify expected error type."""
        cases = runner.load_goldens()

        for case in cases:
            if case["expected_result"] == "fail":
                assert "expected_error_type" in case, \
                    f"Case {case['id']} expected to fail but missing expected_error_type"
