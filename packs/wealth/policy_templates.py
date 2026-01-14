"""
Wealth Pack - Policy Templates.

Defines reusable policy templates for wealth management:
- Portfolio Drift Policy
- Rebalancing Policy
- Suitability Policy
- Concentration Policy
- Tax Loss Harvesting Policy
- Withdrawal Policy
- Correlation Risk Policy
- Fee Change Policy
"""

WEALTH_POLICY_TEMPLATES = {
    "portfolio_drift_policy": {
        "name": "Portfolio Drift Policy",
        "description": "Monitor and escalate when portfolio allocation drifts from target",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "portfolio_drift",
                    "threshold": {
                        "field": "payload.drift_percent",
                        "operator": ">",
                        "value": 5,  # 5% drift threshold
                    },
                    "severity_mapping": {
                        "drift_percent > 15": "critical",
                        "drift_percent > 10": "high",
                        "default": "medium",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "rebalancing_policy": {
        "name": "Rebalancing Policy",
        "description": "Trigger rebalancing based on calendar and threshold rules",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "rebalancing_required",
                    "threshold": {
                        "field": "payload.days_since_rebalance",
                        "operator": ">",
                        "value": 90,  # Quarterly minimum
                    },
                    "severity_mapping": {
                        "days_since_rebalance > 365": "high",
                        "days_since_rebalance > 180": "medium",
                        "default": "low",
                    },
                },
                {
                    "signal_type": "rebalancing_required",
                    "threshold": {
                        "field": "payload.max_drift_percent",
                        "operator": ">",
                        "value": 10,  # 10% max drift triggers rebalance
                    },
                    "severity_mapping": {
                        "max_drift_percent > 15": "high",
                        "default": "medium",
                    },
                },
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "suitability_policy": {
        "name": "Suitability Policy",
        "description": "Ensure portfolio risk matches client risk profile",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "suitability_mismatch",
                    "threshold": {
                        "field": "payload.risk_delta",
                        "operator": "abs>",
                        "value": 1.5,  # 1.5 point risk delta threshold
                    },
                    "severity_mapping": {
                        "risk_delta > 3": "critical",
                        "risk_delta > 2": "high",
                        "risk_delta < -2": "high",  # Too conservative also matters
                        "default": "high",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "concentration_policy": {
        "name": "Concentration Policy",
        "description": "Monitor single position concentration limits",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "concentration_breach",
                    "threshold": {
                        "field": "payload.current_weight_percent",
                        "operator": ">",
                        "value": "payload.limit_percent",
                    },
                    "severity_mapping": {
                        "current_weight_percent > 25": "critical",
                        "current_weight_percent > 15": "high",
                        "default": "medium",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "tax_loss_harvesting_policy": {
        "name": "Tax Loss Harvesting Policy",
        "description": "Identify and escalate tax-loss harvesting opportunities",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "tax_loss_harvest_opportunity",
                    "threshold": {
                        "field": "payload.estimated_tax_savings_usd",
                        "operator": ">",
                        "value": 1000,  # Minimum $1K tax savings
                    },
                    "severity_mapping": {
                        "estimated_tax_savings_usd > 50000": "high",
                        "estimated_tax_savings_usd > 10000": "medium",
                        "default": "low",
                    },
                }
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "withdrawal_policy": {
        "name": "Withdrawal Policy",
        "description": "Monitor and approve large client withdrawal requests",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "client_cash_withdrawal",
                    "threshold": {
                        "field": "payload.withdrawal_percent",
                        "operator": ">",
                        "value": 10,  # 10% withdrawal requires review
                    },
                    "severity_mapping": {
                        "withdrawal_percent > 50": "critical",
                        "withdrawal_percent > 25": "high",
                        "default": "medium",
                    },
                },
                {
                    "signal_type": "client_cash_withdrawal",
                    "threshold": {
                        "field": "payload.withdrawal_amount_usd",
                        "operator": ">",
                        "value": 100000,  # $100K+ requires review
                    },
                    "severity_mapping": {
                        "withdrawal_amount_usd > 1000000": "critical",
                        "withdrawal_amount_usd > 500000": "high",
                        "default": "medium",
                    },
                },
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "correlation_risk_policy": {
        "name": "Correlation Risk Policy",
        "description": "Monitor portfolio diversification and correlation risk",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "market_correlation_spike",
                    "threshold": {
                        "field": "payload.current_correlation",
                        "operator": ">",
                        "value": 0.85,  # High correlation threshold
                    },
                    "severity_mapping": {
                        "current_correlation > 0.95": "critical",
                        "current_correlation > 0.90": "high",
                        "default": "medium",
                    },
                },
                {
                    "signal_type": "market_correlation_spike",
                    "threshold": {
                        "field": "payload.correlation_change",
                        "operator": ">",
                        "value": 0.15,  # Sudden correlation increase
                    },
                    "severity_mapping": {
                        "correlation_change > 0.25": "high",
                        "default": "medium",
                    },
                },
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
    "fee_change_policy": {
        "name": "Fee Change Policy",
        "description": "Manage fee schedule changes and client notifications",
        "rule_definition": {
            "type": "threshold_breach",
            "conditions": [
                {
                    "signal_type": "fee_schedule_change",
                    "threshold": {
                        "field": "payload.change_bps",
                        "operator": ">",
                        "value": 10,  # 10 bps change threshold
                    },
                    "severity_mapping": {
                        "requires_consent == true": "high",
                        "change_bps > 50": "high",
                        "change_bps > 25": "medium",
                        "default": "low",
                    },
                },
                {
                    "signal_type": "fee_schedule_change",
                    "threshold": {
                        "field": "payload.annual_impact_usd",
                        "operator": ">",
                        "value": 1000,  # $1K annual impact
                    },
                    "severity_mapping": {
                        "annual_impact_usd > 10000": "high",
                        "annual_impact_usd > 5000": "medium",
                        "default": "low",
                    },
                },
            ],
            "evaluation_logic": "any_condition_met",
        },
    },
}
