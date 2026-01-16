"""
Treasury Pack - Signal Type Definitions.

Defines the signal types used in treasury management.
"""

TREASURY_SIGNAL_TYPES = {
    "position_limit_breach": {
        "description": "Asset position exceeds configured limit",
        "payload_schema": {
            "asset": "string",
            "current_position": "number",
            "limit": "number",
            "duration_hours": "number",
        },
        "reliability_default": "high",
        "example": {
            "asset": "BTC",
            "current_position": 120,
            "limit": 100,
            "duration_hours": 2
        }
    },
    "market_volatility_spike": {
        "description": "Market volatility exceeds threshold",
        "payload_schema": {
            "asset": "string",
            "volatility": "number",
            "threshold": "number",
            "window_hours": "number",
        },
        "reliability_default": "medium",
        "example": {
            "asset": "BTC",
            "volatility": 0.45,
            "threshold": 0.30,
            "window_hours": 24
        }
    },
    "counterparty_credit_downgrade": {
        "description": "Counterparty credit rating downgraded",
        "payload_schema": {
            "counterparty": "string",
            "previous_rating": "string",
            "new_rating": "string",
            "exposure_usd": "number",
        },
        "reliability_default": "high",
        "example": {
            "counterparty": "Exchange A",
            "previous_rating": "A",
            "new_rating": "BBB",
            "exposure_usd": 5000000
        }
    },
    "liquidity_threshold_breach": {
        "description": "Asset liquidity falls below required threshold",
        "payload_schema": {
            "asset": "string",
            "current_liquidity_ratio": "number",
            "threshold": "number",
        },
        "reliability_default": "high",
        "example": {
            "asset": "ETH",
            "current_liquidity_ratio": 0.15,
            "threshold": 0.20
        }
    },
    "fx_exposure_breach": {
        "description": "Foreign exchange exposure exceeds approved limit",
        "payload_schema": {
            "currency_pair": "string",
            "current_exposure_usd": "number",
            "limit_usd": "number",
            "direction": "string",  # "long" or "short"
        },
        "reliability_default": "high",
        "example": {
            "currency_pair": "EUR/USD",
            "current_exposure_usd": 12500000,
            "limit_usd": 10000000,
            "direction": "long"
        }
    },
    "cash_forecast_variance": {
        "description": "Actual cash position deviates significantly from forecast",
        "payload_schema": {
            "account": "string",
            "forecast_balance_usd": "number",
            "actual_balance_usd": "number",
            "variance_percent": "number",
            "forecast_date": "string",
        },
        "reliability_default": "high",
        "example": {
            "account": "Main Operating Account",
            "forecast_balance_usd": 5000000,
            "actual_balance_usd": 3200000,
            "variance_percent": -36.0,
            "forecast_date": "2026-01-15"
        }
    },
    "covenant_breach": {
        "description": "Financial covenant threshold breached or at risk",
        "payload_schema": {
            "covenant_name": "string",
            "covenant_type": "string",  # "debt_service", "leverage", "liquidity"
            "required_ratio": "number",
            "actual_ratio": "number",
            "lender": "string",
            "facility": "string",
        },
        "reliability_default": "high",
        "example": {
            "covenant_name": "Debt Service Coverage Ratio",
            "covenant_type": "debt_service",
            "required_ratio": 1.25,
            "actual_ratio": 1.18,
            "lender": "Bank of America",
            "facility": "Term Loan A"
        }
    },
    "settlement_failure": {
        "description": "Trade settlement failed or is at risk of failure",
        "payload_schema": {
            "trade_id": "string",
            "asset": "string",
            "counterparty": "string",
            "settlement_date": "string",
            "amount_usd": "number",
            "failure_reason": "string",
        },
        "reliability_default": "high",
        "example": {
            "trade_id": "TRD-2026-0142",
            "asset": "BTC",
            "counterparty": "Prime Broker X",
            "settlement_date": "2026-01-14",
            "amount_usd": 2500000,
            "failure_reason": "insufficient_funds"
        }
    },
    "settlement_rail_shortfall": {
        "description": "Insufficient funds available on a settlement rail to cover required payments",
        "payload_schema": {
            "rail": "string",
            "required_usd": "number",
            "available_usd": "number",
            "shortfall_usd": "number",
            "coverage_ratio": "number",
            "fragmentation_ratio": "number",
            "restricted_cash_usd": "number",
            "root_cause": "string",
        },
        "reliability_default": "high",
        "example": {
            "rail": "Fedwire",
            "required_usd": 15000000,
            "available_usd": 12000000,
            "shortfall_usd": 3000000,
            "coverage_ratio": 0.80,
            "fragmentation_ratio": 0.35,
            "restricted_cash_usd": 2500000,
            "root_cause": "intraday_timing_mismatch"
        }
    },
}
