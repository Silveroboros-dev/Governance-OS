"""
Treasury Pack - Policy Templates.

Defines reusable policy templates for treasury management.

All policies use event_trigger type: the signal itself represents
the breach/event. Policies trigger on signal existence to generate exceptions.
"""

TREASURY_POLICY_TEMPLATES = {
    "position_limit_policy": {
        "name": "Position Limit Policy",
        "description": "Enforce position limits per asset with escalation on breach",
        "rule_definition": {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "position_limit_breach",
                    "threshold": {
                        "field": "payload.current_position",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "high",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "volatility_policy": {
        "name": "Market Volatility Policy",
        "description": "Monitor and escalate on volatility spikes",
        "rule_definition": {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "market_volatility_spike",
                    "threshold": {
                        "field": "payload.volatility",
                        "operator": "exists",
                        "value": True,
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
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "counterparty_credit_downgrade",
                    "threshold": {
                        "field": "payload.counterparty",
                        "operator": "exists",
                        "value": True,
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
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "liquidity_threshold_breach",
                    "threshold": {
                        "field": "payload.current_ratio",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "high",
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
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "fx_exposure_breach",
                    "threshold": {
                        "field": "payload.current_exposure",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "high",
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
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "cash_forecast_variance",
                    "threshold": {
                        "field": "payload.variance_percent",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "high",
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
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "covenant_breach",
                    "threshold": {
                        "field": "payload.covenant_name",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "critical",
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
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "settlement_failure",
                    "threshold": {
                        "field": "payload.failure_reason",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "high",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "settlement_rail_policy": {
        "name": "Settlement Rail Policy",
        "description": "Escalate settlement rail shortfalls",
        "rule_definition": {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "settlement_rail_shortfall",
                    "threshold": {
                        "field": "payload.shortfall",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "high",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "debt_maturity_policy": {
        "name": "Debt Maturity Policy",
        "description": "Escalate approaching debt maturities for refinancing review",
        "rule_definition": {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "debt_maturity_approaching",
                    "threshold": {
                        "field": "payload.maturity_date",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "high",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "interest_rate_reset_policy": {
        "name": "Interest Rate Reset Policy",
        "description": "Escalate approaching interest rate resets",
        "rule_definition": {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "interest_rate_reset",
                    "threshold": {
                        "field": "payload.reset_date",
                        "operator": "exists",
                        "value": True,
                    },
                    "severity_mapping": {
                        "default": "medium",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "bank_account_anomaly_policy": {
        "name": "Bank Account Anomaly Policy",
        "description": "Escalate unusual bank account activity",
        "rule_definition": {
            "type": "event_trigger",
            "conditions": [
                {
                    "signal_type": "bank_account_anomaly",
                    "threshold": {
                        "field": "payload.anomaly_type",
                        "operator": "exists",
                        "value": True,
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
