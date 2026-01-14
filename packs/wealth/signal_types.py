"""
Wealth Pack - Signal Types.

Defines the 8 signal types for wealth management:
- portfolio_drift
- rebalancing_required
- suitability_mismatch
- concentration_breach
- tax_loss_harvest_opportunity
- client_cash_withdrawal
- market_correlation_spike
- fee_schedule_change
"""

WEALTH_SIGNAL_TYPES = {
    "portfolio_drift": {
        "description": "Portfolio allocation has drifted from target allocation",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "asset_class": "string",  # equities, fixed_income, alternatives, cash
            "target_allocation_percent": "number",
            "current_allocation_percent": "number",
            "drift_percent": "number",  # absolute difference
            "drift_direction": "string",  # over, under
            "portfolio_value_usd": "number",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "drift_percent > 10": "high",
            "drift_percent > 15": "critical",
            "portfolio_value_usd > 10000000 and drift_percent > 5": "high",
        },
    },
    "rebalancing_required": {
        "description": "Portfolio rebalancing threshold has been triggered",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "trigger_type": "string",  # calendar, threshold, tax_event
            "last_rebalance_date": "string",
            "days_since_rebalance": "number",
            "max_drift_percent": "number",  # largest drift across asset classes
            "estimated_trades": "number",
            "estimated_tax_impact_usd": "number",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "days_since_rebalance > 365": "high",
            "estimated_tax_impact_usd > 50000": "high",
        },
    },
    "suitability_mismatch": {
        "description": "Client's holdings do not match their risk profile",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "client_risk_score": "number",  # 1-10
            "portfolio_risk_score": "number",  # 1-10
            "risk_delta": "number",  # portfolio - client
            "mismatch_direction": "string",  # too_aggressive, too_conservative
            "top_contributing_holdings": "array",  # list of holdings causing mismatch
            "last_profile_update": "string",
        },
        "severity_default": "high",
        "escalation_rules": {
            "abs(risk_delta) > 3": "critical",
            "mismatch_direction == 'too_aggressive' and risk_delta > 2": "critical",
        },
    },
    "concentration_breach": {
        "description": "Single position exceeds concentration limit",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "security_id": "string",
            "security_name": "string",
            "sector": "string",
            "current_weight_percent": "number",
            "limit_percent": "number",
            "breach_amount_percent": "number",
            "position_value_usd": "number",
            "is_restricted_security": "boolean",
        },
        "severity_default": "high",
        "escalation_rules": {
            "current_weight_percent > 20": "critical",
            "is_restricted_security == true": "critical",
            "position_value_usd > 1000000": "high",
        },
    },
    "tax_loss_harvest_opportunity": {
        "description": "Tax-loss harvesting opportunity identified",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "security_id": "string",
            "security_name": "string",
            "cost_basis_usd": "number",
            "current_value_usd": "number",
            "unrealized_loss_usd": "number",
            "holding_period_days": "number",
            "is_short_term": "boolean",
            "wash_sale_risk": "boolean",
            "replacement_security_id": "string",
            "estimated_tax_savings_usd": "number",
        },
        "severity_default": "low",
        "escalation_rules": {
            "estimated_tax_savings_usd > 10000": "medium",
            "estimated_tax_savings_usd > 50000": "high",
            "is_short_term == false and unrealized_loss_usd > 25000": "medium",
        },
    },
    "client_cash_withdrawal": {
        "description": "Large cash withdrawal request from client",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "withdrawal_amount_usd": "number",
            "withdrawal_percent": "number",  # percent of portfolio
            "available_cash_usd": "number",
            "liquidation_required": "boolean",
            "liquidation_amount_usd": "number",
            "withdrawal_reason": "string",
            "requested_date": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "withdrawal_percent > 25": "high",
            "withdrawal_percent > 50": "critical",
            "liquidation_required == true and liquidation_amount_usd > 500000": "high",
        },
    },
    "market_correlation_spike": {
        "description": "Portfolio correlation with market has spiked unexpectedly",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "benchmark": "string",  # SP500, ACWI, etc.
            "current_correlation": "number",  # -1 to 1
            "historical_correlation": "number",
            "correlation_change": "number",
            "lookback_days": "number",
            "diversification_ratio": "number",
            "risk_parity_breach": "boolean",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "current_correlation > 0.95": "high",
            "correlation_change > 0.2": "high",
            "risk_parity_breach == true": "high",
        },
    },
    "fee_schedule_change": {
        "description": "Fee schedule change affecting client",
        "payload_schema": {
            "client_id": "string",
            "portfolio_id": "string",
            "fee_type": "string",  # management, custody, trading, performance
            "current_rate_bps": "number",
            "new_rate_bps": "number",
            "change_bps": "number",
            "effective_date": "string",
            "annual_impact_usd": "number",
            "requires_client_notification": "boolean",
            "requires_consent": "boolean",
        },
        "severity_default": "low",
        "escalation_rules": {
            "change_bps > 25": "medium",
            "annual_impact_usd > 5000": "medium",
            "requires_consent == true": "high",
        },
    },
}
