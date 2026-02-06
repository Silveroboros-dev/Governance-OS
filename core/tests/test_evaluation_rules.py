"""
Tests for evaluation rules domain logic.

These tests validate the deterministic evaluation logic that applies
policy rules to signals.
"""

import pytest
from uuid import uuid4

from core.domain.evaluation_rules import (
    evaluate_policy,
    RuleType,
    _evaluate_threshold_breach,
    _evaluate_event_trigger,
)


class TestEventTriggerObservationFiltering:
    """
    CRITICAL: Event triggers must NOT return FAIL on observations.

    This is a regression test for the fix that ensures observations
    (event-category signals) cannot cause policy FAIL. FAIL has a
    specific meaning: "a rule was violated." Observations may generate
    review tasks outside the evaluator, but they don't violate rules.
    """

    def test_event_trigger_observation_does_not_fail(self):
        """
        REGRESSION TEST: Event trigger with observation signal returns PASS, not FAIL.

        Scenario:
        - Policy has an event_trigger rule checking for risk_tolerance_change
        - Input signal matches the rule but has canonical_status="observation"
        - Expected: evaluator returns PASS (not FAIL)
        """
        rule_definition = {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "risk_tolerance_change",
                    "threshold": {
                        "field": "payload.new_tolerance",
                        "operator": "exists",
                        "value": True
                    },
                    "severity_mapping": {
                        "default": "high"
                    }
                }
            ],
            "evaluation_logic": "any_condition_met"
        }

        # Signal matches the rule but is an observation
        signals = [
            {
                "id": uuid4(),
                "signal_type": "risk_tolerance_change",
                "payload": {
                    "client": "Jane Doe",
                    "new_tolerance": "aggressive",
                    "previous_tolerance": "moderate"
                },
                "canonical_status": "observation",  # KEY: this is an observation
                "severity": "high",
            }
        ]

        result, details = evaluate_policy(rule_definition, signals)

        # MUST NOT be "fail" — observations cannot cause FAIL
        assert result == "pass", (
            f"Event trigger returned '{result}' on observation signal. "
            "Observations must not cause FAIL. This is a regression."
        )

        # The observation should be tracked in details
        assert len(details.get("observation_signals", [])) == 1
        assert details["conditions_matched"] == 0

    def test_event_trigger_breach_does_fail(self):
        """
        Event trigger with breach signal should return FAIL.

        This confirms the filter only excludes observations, not breaches.
        """
        rule_definition = {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "risk_tolerance_change",
                    "threshold": {
                        "field": "payload.new_tolerance",
                        "operator": "exists",
                        "value": True
                    },
                    "severity_mapping": {
                        "default": "high"
                    }
                }
            ],
            "evaluation_logic": "any_condition_met"
        }

        # Signal matches the rule and IS a breach
        signals = [
            {
                "id": uuid4(),
                "signal_type": "risk_tolerance_change",
                "payload": {
                    "client": "Jane Doe",
                    "new_tolerance": "aggressive",
                    "previous_tolerance": "moderate"
                },
                "canonical_status": "breach",  # This is a breach
                "severity": "high",
            }
        ]

        result, details = evaluate_policy(rule_definition, signals)

        # Breach signals CAN cause FAIL
        assert result == "fail"
        assert details["conditions_matched"] == 1

    def test_event_trigger_null_status_backward_compatibility(self):
        """
        Event trigger with null canonical_status should return FAIL (backward compatibility).

        Signals without canonical_status (from before the Canonicalizer) should
        be treated as potential breaches for backward compatibility.
        """
        rule_definition = {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "risk_tolerance_change",
                    "threshold": {
                        "field": "payload.new_tolerance",
                        "operator": "exists",
                        "value": True
                    },
                    "severity_mapping": {
                        "default": "high"
                    }
                }
            ],
            "evaluation_logic": "any_condition_met"
        }

        # Signal without canonical_status (legacy signal)
        signals = [
            {
                "id": uuid4(),
                "signal_type": "risk_tolerance_change",
                "payload": {
                    "client": "Jane Doe",
                    "new_tolerance": "aggressive",
                    "previous_tolerance": "moderate"
                },
                # No canonical_status — backward compatibility
            }
        ]

        result, details = evaluate_policy(rule_definition, signals)

        # Legacy signals (null status) should still cause FAIL
        assert result == "fail"
        assert details["conditions_matched"] == 1


class TestThresholdBreachObservationFiltering:
    """
    Confirm threshold_breach rules also filter out observations.

    This ensures consistency between rule types.
    """

    def test_threshold_breach_observation_does_not_fail(self):
        """
        Threshold breach with observation signal returns PASS, not FAIL.
        """
        rule_definition = {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "position_limit_breach",
                    "threshold": {
                        "field": "payload.current_position",
                        "operator": ">",
                        "value": "payload.limit"
                    },
                    "severity_mapping": {
                        "default": "high"
                    }
                }
            ],
            "evaluation_logic": "any_condition_met"
        }

        # Signal matches but is an observation
        signals = [
            {
                "id": uuid4(),
                "signal_type": "position_limit_breach",
                "payload": {
                    "asset": "BTC",
                    "current_position": 120,
                    "limit": 100
                },
                "canonical_status": "observation",  # Downgraded by Canonicalizer
                "severity": "high",
            }
        ]

        result, details = evaluate_policy(rule_definition, signals)

        # Observations cannot cause FAIL
        assert result == "pass"
        assert len(details.get("observation_signals", [])) == 1
        assert details["conditions_matched"] == 0

    def test_threshold_breach_breach_does_fail(self):
        """
        Threshold breach with breach signal should return FAIL.
        """
        rule_definition = {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "position_limit_breach",
                    "threshold": {
                        "field": "payload.current_position",
                        "operator": ">",
                        "value": "payload.limit"
                    },
                    "severity_mapping": {
                        "default": "high"
                    }
                }
            ],
            "evaluation_logic": "any_condition_met"
        }

        # Signal matches and IS a breach
        signals = [
            {
                "id": uuid4(),
                "signal_type": "position_limit_breach",
                "payload": {
                    "asset": "BTC",
                    "current_position": 120,
                    "limit": 100
                },
                "canonical_status": "breach",
                "severity": "high",
            }
        ]

        result, details = evaluate_policy(rule_definition, signals)

        # Breach signals CAN cause FAIL
        assert result == "fail"
        assert details["conditions_matched"] == 1
