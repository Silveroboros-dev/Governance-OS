"""
Policy evaluation rule execution engine.

This module implements the deterministic evaluation logic that applies
policy rules to signals and produces structured evaluation results.

CRITICAL: All evaluation logic must be deterministic.
"""

from typing import Dict, List, Any, Tuple
from enum import Enum


class RuleType(str, Enum):
    """Supported rule types."""
    THRESHOLD_BREACH = "threshold_breach"
    PATTERN_MATCH = "pattern_match"
    AGGREGATION = "aggregation"
    EVENT_TRIGGER = "event_trigger"


class ConditionOperator(str, Enum):
    """Supported comparison operators."""
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="


def evaluate_policy(
    rule_definition: Dict[str, Any],
    signals: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Execute policy evaluation against signals.

    Args:
        rule_definition: Policy rule definition (JSONB from PolicyVersion)
        signals: List of signal dictionaries

    Returns:
        Tuple of (result, details) where:
        - result: "pass" | "fail" | "inconclusive"
        - details: Structured explanation dict

    Example rule_definition:
        {
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
                        "duration_hours < 1": "medium",
                        "duration_hours >= 1": "high"
                    }
                }
            ],
            "evaluation_logic": "any_condition_met"
        }
    """
    rule_type = rule_definition.get("type")

    if rule_type == RuleType.THRESHOLD_BREACH:
        return _evaluate_threshold_breach(rule_definition, signals)
    elif rule_type == RuleType.PATTERN_MATCH:
        return _evaluate_pattern_match(rule_definition, signals)
    elif rule_type == RuleType.AGGREGATION:
        return _evaluate_aggregation(rule_definition, signals)
    elif rule_type == RuleType.EVENT_TRIGGER:
        return _evaluate_event_trigger(rule_definition, signals)
    else:
        return "inconclusive", {"error": f"Unknown rule type: {rule_type}"}


def _evaluate_threshold_breach(
    rule_definition: Dict[str, Any],
    signals: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Evaluate threshold breach rules.

    Checks if any/all signals meet threshold conditions.

    IMPORTANT: Respects canonical_status from the Canonicalizer.
    Signals with canonical_status="observation" are EXCLUDED from breach matching.
    Only signals with canonical_status="breach" (or None for backward compatibility)
    can trigger policy failures.
    """
    conditions = rule_definition.get("conditions", [])
    evaluation_logic = rule_definition.get("evaluation_logic", "any_condition_met")

    matched_conditions = []
    matched_signals = []
    observation_signals = []  # Track observations for audit

    for condition in conditions:
        signal_type = condition["signal_type"]
        threshold = condition["threshold"]

        # Filter signals by type
        relevant_signals = [s for s in signals if s["signal_type"] == signal_type]

        for signal in relevant_signals:
            if _check_threshold(signal, threshold):
                # Check canonical_status from Canonicalizer
                # Only "breach" status signals can trigger policy failures
                canonical_status = signal.get("canonical_status")

                if canonical_status == "observation":
                    # Signal was downgraded by Canonicalizer — cannot trigger breach
                    observation_signals.append(signal)
                    continue

                # canonical_status is "breach" or None (backward compatibility)
                matched_conditions.append(condition)
                matched_signals.append(signal)
                break  # One match per condition

    # Determine result based on evaluation logic
    if evaluation_logic == "any_condition_met":
        result = "fail" if matched_conditions else "pass"
    elif evaluation_logic == "all_conditions_met":
        result = "fail" if len(matched_conditions) == len(conditions) else "pass"
    else:
        result = "inconclusive"

    details = {
        "rule_type": "threshold_breach",
        "evaluation_logic": evaluation_logic,
        "conditions_evaluated": len(conditions),
        "conditions_matched": len(matched_conditions),
        "matched_signals": [{"id": str(s["id"]), "type": s["signal_type"]} for s in matched_signals],
        "observation_signals": [{"id": str(s["id"]), "type": s["signal_type"]} for s in observation_signals],
        "severity": _determine_severity(matched_signals, conditions) if matched_signals else None
    }

    return result, details


def _check_threshold(signal: Dict[str, Any], threshold: Dict[str, Any]) -> bool:
    """
    Check if signal meets threshold condition.

    Args:
        signal: Signal dictionary
        threshold: Threshold definition with field, operator, value

    Returns:
        True if threshold is breached, False otherwise
    """
    field_path = threshold["field"]  # e.g., "payload.current_position"
    operator = threshold["operator"]
    value_expr = threshold["value"]  # e.g., "payload.limit" or literal value

    # Extract field value from signal
    field_value = _extract_field_value(signal, field_path)

    # Extract or evaluate comparison value
    if isinstance(value_expr, str) and value_expr.startswith("payload."):
        comparison_value = _extract_field_value(signal, value_expr)
    else:
        comparison_value = value_expr

    # Perform comparison
    return _compare_values(field_value, operator, comparison_value)


def _extract_field_value(data: Dict[str, Any], field_path: str) -> Any:
    """
    Extract nested field value from dictionary using dot notation.

    Example:
        >>> data = {"payload": {"current_position": 120}}
        >>> _extract_field_value(data, "payload.current_position")
        120
    """
    parts = field_path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def _compare_values(left: Any, operator: str, right: Any) -> bool:
    """
    Compare two values using the specified operator.

    Args:
        left: Left operand
        operator: Comparison operator (>, >=, <, <=, ==, !=)
        right: Right operand

    Returns:
        Comparison result
    """
    try:
        if operator == ">":
            return left > right
        elif operator == ">=":
            return left >= right
        elif operator == "<":
            return left < right
        elif operator == "<=":
            return left <= right
        elif operator == "==":
            return left == right
        elif operator == "!=":
            return left != right
        else:
            return False
    except (TypeError, ValueError):
        return False


def _determine_severity(
    matched_signals: List[Dict[str, Any]],
    conditions: List[Dict[str, Any]]
) -> str:
    """
    Determine exception severity based on severity mapping in conditions.

    Args:
        matched_signals: Signals that triggered the exception
        conditions: Condition definitions with severity_mapping

    Returns:
        Severity level: "critical" | "high" | "medium" | "low"
    """
    # For now, use simple logic: check duration-based mapping
    # In production, this would be more sophisticated

    if not matched_signals or not conditions:
        return "medium"

    # Get first matched signal and condition
    signal = matched_signals[0]
    condition = conditions[0]

    severity_mapping = condition.get("severity_mapping", {})

    # Check payload for duration_hours
    duration = signal.get("payload", {}).get("duration_hours", 0)

    # Apply severity mapping rules (simplified)
    if duration >= 4:
        return severity_mapping.get("duration_hours >= 4", "critical")
    elif duration >= 1:
        return severity_mapping.get("duration_hours >= 1", "high")
    else:
        return severity_mapping.get("default", "medium")


def _evaluate_pattern_match(
    rule_definition: Dict[str, Any],
    signals: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Evaluate pattern matching rules.

    Placeholder for Sprint 2+.
    """
    return "inconclusive", {"error": "Pattern matching not yet implemented"}


def _evaluate_aggregation(
    rule_definition: Dict[str, Any],
    signals: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Evaluate aggregation rules.

    Placeholder for Sprint 2+.
    """
    return "inconclusive", {"error": "Aggregation rules not yet implemented"}


def _evaluate_event_trigger(
    rule_definition: Dict[str, Any],
    signals: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Evaluate event trigger rules.

    Triggers on the existence of specific signal types, optionally checking
    that a field exists. Used for policies like "any risk_tolerance_change
    signal requires review".

    IMPORTANT: Consistent with threshold rules, only signals with
    canonical_status="breach" can cause FAIL. Event-category signals are
    always observations; they may generate review tasks outside the evaluator
    but do not cause FAIL here. This preserves the semantic meaning of FAIL
    as "a rule was violated" rather than "something needs review."

    Example rule_definition:
        {
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
    """
    conditions = rule_definition.get("conditions", [])
    evaluation_logic = rule_definition.get("evaluation_logic", "any_condition_met")

    matched_conditions = []
    matched_signals = []
    observation_signals = []  # Track observations for audit

    for condition in conditions:
        signal_type = condition["signal_type"]
        threshold = condition.get("threshold", {})

        # Filter signals by type
        relevant_signals = [s for s in signals if s["signal_type"] == signal_type]

        for signal in relevant_signals:
            # Check if signal matches trigger condition
            if _check_event_trigger(signal, threshold):
                # Check canonical_status from Canonicalizer
                # Only "breach" status signals can trigger policy failures
                canonical_status = signal.get("canonical_status")

                if canonical_status == "observation":
                    # Signal is an observation — cannot trigger FAIL
                    # May generate review tasks outside evaluator
                    observation_signals.append(signal)
                    continue

                # canonical_status is "breach" or None (backward compatibility)
                matched_conditions.append(condition)
                matched_signals.append(signal)
                break  # One match per condition

    # Determine result based on evaluation logic
    # Only breach signals can cause FAIL; observations are tracked but don't fail
    if evaluation_logic == "any_condition_met":
        result = "fail" if matched_conditions else "pass"
    elif evaluation_logic == "all_conditions_met":
        result = "fail" if len(matched_conditions) == len(conditions) else "pass"
    else:
        result = "inconclusive"

    # Use canonical severity from signals if available
    severity = _determine_event_severity(matched_signals, conditions) if matched_signals else None
    if matched_signals and matched_signals[0].get("severity"):
        severity = matched_signals[0].get("severity")

    details = {
        "rule_type": "event_trigger",
        "evaluation_logic": evaluation_logic,
        "conditions_evaluated": len(conditions),
        "conditions_matched": len(matched_conditions),
        "matched_signals": [{"id": str(s["id"]), "type": s["signal_type"], "canonical_status": s.get("canonical_status")} for s in matched_signals],
        "observation_signals": [{"id": str(s["id"]), "type": s["signal_type"]} for s in observation_signals],
        "severity": severity
    }

    return result, details


def _check_event_trigger(signal: Dict[str, Any], threshold: Dict[str, Any]) -> bool:
    """
    Check if signal meets event trigger condition.

    For event triggers, the main operators are:
    - "exists": Check if a field exists and is truthy
    - "not_exists": Check if a field doesn't exist or is falsy
    """
    if not threshold:
        # No threshold means signal existence alone is enough
        return True

    field_path = threshold.get("field", "")
    operator = threshold.get("operator", "exists")
    expected = threshold.get("value", True)

    # Extract field value
    field_value = _extract_field_value(signal, field_path)

    if operator == "exists":
        # Check if field exists and is truthy (or matches expected value)
        if expected is True:
            return field_value is not None
        else:
            return field_value is None

    # Fall back to regular comparison for other operators
    return _compare_values(field_value, operator, expected)


def _determine_event_severity(
    matched_signals: List[Dict[str, Any]],
    conditions: List[Dict[str, Any]]
) -> str:
    """
    Determine severity for event trigger policies.

    Event triggers typically use "default" severity from the mapping.
    """
    if not matched_signals or not conditions:
        return "medium"

    condition = conditions[0]
    severity_mapping = condition.get("severity_mapping", {})

    # For event triggers, use default severity
    return severity_mapping.get("default", "high")
