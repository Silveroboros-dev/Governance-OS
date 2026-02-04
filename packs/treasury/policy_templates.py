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
    "liquidity_policy": {
        "name": "Liquidity Management Policy",
        "description": "Ensure adequate liquidity across asset classes",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "liquidity_threshold_breach",
                    "threshold": {
                        # Supports both ratio-based and amount-based signals
                        "field": "payload.current_amount",
                        "operator": "<",
                        "value": "payload.threshold_amount",
                    },
                    "severity_mapping": {
                        "default": "high"
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "fx_exposure_policy": {
        "name": "FX Exposure Policy",
        "description": "Monitor and control foreign exchange exposure limits",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "fx_exposure_breach",
                    "threshold": {
                        # Trigger on any unhedged FX exposure with material notional
                        "field": "payload.notional",
                        "operator": ">",
                        "value": 50000,  # $50K threshold for unhedged exposure
                    },
                    "severity_mapping": {
                        "default": "high"
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "cash_management_policy": {
        "name": "Cash Forecasting Policy",
        "description": "Monitor cash position variances from forecasts",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "cash_forecast_variance",
                    "threshold": {
                        # Trigger on material variance amounts
                        "field": "payload.variance_amount",
                        "operator": ">",
                        "value": 10000,  # $10K variance threshold
                    },
                    "severity_mapping": {
                        "default": "high"
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "covenant_monitoring_policy": {
        "name": "Covenant Monitoring Policy",
        "description": "Monitor financial covenant compliance",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "covenant_breach",
                    "threshold": {
                        # Supports value-based covenant signals
                        "field": "payload.actual_value",
                        "operator": "<",
                        "value": "payload.required_value",
                    },
                    "severity_mapping": {
                        "default": "critical"  # Covenant breaches are always critical
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "settlement_policy": {
        "name": "Settlement Risk Policy",
        "description": "Monitor and escalate trade settlement failures",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "settlement_failure",
                    "threshold": {
                        "field": "payload.amount_usd",
                        "operator": ">",
                        "value": 100000,  # Escalate failures > $100K
                    },
                    "severity_mapping": {
                        "amount_usd > 1000000": "critical",
                        "amount_usd > 500000": "high",
                        "default": "medium"
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
}
