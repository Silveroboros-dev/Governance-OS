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
                        "field": "payload.current_liquidity_ratio",
                        "operator": "<",
                        "value": "payload.threshold",
                    },
                    "severity_mapping": {
                        "current_liquidity_ratio < threshold * 0.5": "critical",
                        "current_liquidity_ratio < threshold * 0.75": "high",
                        "default": "medium"
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
                        "field": "payload.current_exposure_usd",
                        "operator": ">",
                        "value": "payload.limit_usd",
                    },
                    "severity_mapping": {
                        "current_exposure_usd > limit_usd * 1.25": "critical",
                        "current_exposure_usd > limit_usd * 1.10": "high",
                        "default": "medium"
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
                        "field": "payload.variance_percent",
                        "operator": "abs>",  # Absolute value comparison
                        "value": 20,  # 20% variance threshold
                    },
                    "severity_mapping": {
                        "variance_percent < -30": "critical",  # Significantly below forecast
                        "variance_percent < -20": "high",
                        "variance_percent > 30": "medium",  # Above forecast is less urgent
                        "default": "medium"
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
                        "field": "payload.actual_ratio",
                        "operator": "<",
                        "value": "payload.required_ratio",
                    },
                    "severity_mapping": {
                        "actual_ratio < required_ratio * 0.90": "critical",  # 10%+ below
                        "actual_ratio < required_ratio * 0.95": "high",
                        "default": "high"
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
