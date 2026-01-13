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
    else:
        return "inconclusive", {"error": f"Unknown rule type: {rule_type}"}


def _evaluate_threshold_breach(
    rule_definition: Dict[str, Any],
    signals: List[Dict[str, Any]]
) -> Tuple[str, Dict[str, Any]]:
    """
    Evaluate threshold breach rules.

    Checks if any/all signals meet threshold conditions.
    """
    conditions = rule_definition.get("conditions", [])
    evaluation_logic = rule_definition.get("evaluation_logic", "any_condition_met")

    matched_conditions = []
    matched_signals = []

    for condition in conditions:
        signal_type = condition["signal_type"]
        threshold = condition["threshold"]

        # Filter signals by type
        relevant_signals = [s for s in signals if s["signal_type"] == signal_type]

        for signal in relevant_signals:
            if _check_threshold(signal, threshold):
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
