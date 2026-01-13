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
}
