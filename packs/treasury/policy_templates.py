"""
Treasury Pack - Policy Templates.

Defines reusable policy templates for treasury management.
"""

TREASURY_POLICY_TEMPLATES = {
    "position_limit_policy": {
        "name": "Position Limit Policy",
        "description": "Enforce position limits per asset with escalation on breach",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "position_limit_breach",
                    "threshold": {
                        "field": "payload.current_position",
                        "operator": ">",
                        "value": "payload.limit",
                    },
                    "severity_mapping": {
                        "duration_hours < 1": "medium",
                        "duration_hours >= 1 and duration_hours < 4": "high",
                        "duration_hours >= 4": "critical",
                        "default": "medium"
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",  # 'any' or 'all'
        },
    },
    "volatility_policy": {
        "name": "Market Volatility Policy",
        "description": "Monitor and escalate on volatility spikes",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "market_volatility_spike",
                    "threshold": {
                        "field": "payload.volatility",
                        "operator": ">",
                        "value": "payload.threshold",
                    },
                    "severity_mapping": {
                        "default": "high",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "credit_risk_policy": {
        "name": "Counterparty Credit Risk Policy",
        "description": "Monitor counterparty credit ratings and exposure",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "counterparty_credit_downgrade",
                    "threshold": {
                        "field": "payload.exposure_usd",
                        "operator": ">",
                        "value": 1000000,  # $1M threshold
                    },
                    "severity_mapping": {
                        "default": "high",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
}
