"""
Treasury Pack - Signal Types.

Defines canonical signal types for treasury management with:
- Required payload fields for deterministic extraction
- Title templates for consistent, auditable naming
- Severity rules for policy evaluation

IMPORTANT: LLM extracts structured facts into payload fields.
Titles are generated deterministically from templates - never LLM-invented.
"""

TREASURY_SIGNAL_TYPES = {
    "position_limit_breach": {
        "description": "Asset position exceeds configured limit",
        "title_template": "POSITION_LIMIT_BREACH: {asset} ({current_position} vs {limit} limit)",
        "required_fields": ["asset", "current_position", "limit"],
        "payload_schema": {
            "asset": "string",  # asset identifier (BTC, ETH, etc.)
            "current_position": "string",  # current position with unit
            "limit": "string",  # limit value with unit
            "duration_hours": "number",  # how long breach has persisted
            "breach_percent": "string",  # % over limit
            "entity": "string",  # trading entity
            "evidence_text": "string",  # source quote
        },
        "severity_default": "high",
        "escalation_rules": {
            "breach_percent > 50": "critical",
            "duration_hours > 24": "critical",
        },
    },
    "market_volatility_spike": {
        "description": "Market volatility exceeds threshold",
        "title_template": "VOLATILITY_SPIKE: {asset} ({volatility} vs {threshold} threshold)",
        "required_fields": ["asset", "volatility", "threshold"],
        "payload_schema": {
            "asset": "string",  # asset identifier
            "volatility": "string",  # volatility measure with unit
            "threshold": "string",  # threshold value
            "window_hours": "number",  # measurement window
            "measure_type": "string",  # realized, implied, etc.
            "evidence_text": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "volatility > 0.50": "high",
            "volatility > 0.75": "critical",
        },
    },
    "counterparty_credit_downgrade": {
        "description": "Counterparty credit rating downgraded",
        "title_template": "CREDIT_DOWNGRADE: {counterparty} ({previous_rating} -> {new_rating})",
        "required_fields": ["counterparty", "previous_rating", "new_rating"],
        "payload_schema": {
            "counterparty": "string",  # counterparty name
            "previous_rating": "string",  # prior credit rating
            "new_rating": "string",  # new credit rating
            "rating_agency": "string",  # S&P, Moody's, Fitch
            "exposure_usd": "string",  # current exposure amount
            "evidence_text": "string",
        },
        "severity_default": "high",
        "escalation_rules": {
            "new_rating contains 'BB'": "critical",
            "new_rating contains 'B'": "critical",
            "new_rating contains 'C'": "critical",
        },
    },
    "liquidity_threshold_breach": {
        "description": "Asset liquidity falls below required threshold",
        "title_template": "LIQUIDITY_BREACH: {entity} ({current_ratio} vs {threshold} required)",
        "required_fields": ["entity", "current_ratio", "threshold"],
        "payload_schema": {
            "entity": "string",  # entity or account name
            "asset": "string",  # affected asset if specific
            "current_ratio": "string",  # current liquidity ratio
            "threshold": "string",  # required threshold
            "shortfall_usd": "string",  # dollar shortfall if known
            "currency": "string",
            "evidence_text": "string",
        },
        "severity_default": "high",
        "escalation_rules": {
            "current_ratio < 0.10": "critical",
        },
    },
    "fx_exposure_breach": {
        "description": "Foreign exchange exposure exceeds approved limit",
        "title_template": "FX_EXPOSURE_BREACH: {currency_pair} ({current_exposure} vs {limit} limit, {direction})",
        "required_fields": ["currency_pair", "current_exposure", "limit", "direction"],
        "payload_schema": {
            "currency_pair": "string",  # e.g., EUR/USD
            "current_exposure": "string",  # current exposure with currency
            "limit": "string",  # limit value
            "direction": "string",  # long or short
            "breach_percent": "string",  # % over limit
            "hedge_recommendation": "string",  # if mentioned
            "evidence_text": "string",
        },
        "severity_default": "high",
        "escalation_rules": {
            "breach_percent > 25": "critical",
        },
    },
    "cash_forecast_variance": {
        "description": "Actual cash position deviates significantly from forecast",
        "title_template": "CASH_VARIANCE: {account} ({variance_percent} variance, {actual} vs {forecast})",
        "required_fields": ["account", "actual", "forecast", "variance_percent"],
        "payload_schema": {
            "account": "string",  # account name
            "forecast": "string",  # forecasted balance
            "actual": "string",  # actual balance
            "variance_percent": "string",  # variance as percentage
            "variance_direction": "string",  # positive or negative
            "forecast_date": "string",  # date of forecast
            "root_cause": "string",  # if identified
            "evidence_text": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "variance_percent < -25": "high",
            "variance_percent < -50": "critical",
        },
    },
    "covenant_breach": {
        "description": "Financial covenant threshold breached or at risk",
        "title_template": "COVENANT_BREACH: {covenant_name} ({actual_ratio} vs {required_ratio} required)",
        "required_fields": ["covenant_name", "actual_ratio", "required_ratio"],
        "payload_schema": {
            "covenant_name": "string",  # covenant description
            "covenant_type": "string",  # debt_service, leverage, liquidity
            "required_ratio": "string",  # required value
            "actual_ratio": "string",  # actual value
            "lender": "string",  # lender name
            "facility": "string",  # facility name
            "cure_period_days": "number",  # days to cure if known
            "evidence_text": "string",
        },
        "severity_default": "critical",
        "escalation_rules": {},
    },
    "settlement_failure": {
        "description": "Trade settlement failed or is at risk of failure",
        "title_template": "SETTLEMENT_FAILURE: {counterparty} ({amount}, {failure_reason})",
        "required_fields": ["counterparty", "amount", "failure_reason"],
        "payload_schema": {
            "trade_id": "string",  # trade identifier
            "asset": "string",  # asset involved
            "counterparty": "string",  # counterparty name
            "settlement_date": "string",
            "amount": "string",  # settlement amount with currency
            "failure_reason": "string",  # reason for failure
            "evidence_text": "string",
        },
        "severity_default": "high",
        "escalation_rules": {
            "failure_reason == 'insufficient_funds'": "critical",
        },
    },
    "settlement_rail_shortfall": {
        "description": "Insufficient funds available on a settlement rail",
        "title_template": "RAIL_SHORTFALL: {rail} ({shortfall} shortfall, {coverage_ratio} coverage)",
        "required_fields": ["rail", "shortfall", "coverage_ratio"],
        "payload_schema": {
            "rail": "string",  # Fedwire, SWIFT, etc.
            "required": "string",  # required amount
            "available": "string",  # available amount
            "shortfall": "string",  # shortfall amount
            "coverage_ratio": "string",  # available/required
            "fragmentation_ratio": "string",  # if applicable
            "restricted_cash": "string",  # restricted funds
            "root_cause": "string",  # timing mismatch, etc.
            "evidence_text": "string",
        },
        "severity_default": "critical",
        "escalation_rules": {},
    },
    "debt_maturity_approaching": {
        "description": "Debt facility approaching maturity requiring refinancing decision",
        "title_template": "DEBT_MATURITY: {facility} ({amount}, matures {maturity_date})",
        "required_fields": ["facility", "amount", "maturity_date"],
        "payload_schema": {
            "facility": "string",  # facility name
            "lender": "string",  # lender name
            "amount": "string",  # principal amount
            "maturity_date": "string",  # maturity date
            "days_to_maturity": "number",
            "current_rate": "string",  # current interest rate
            "refinance_status": "string",  # if discussions ongoing
            "evidence_text": "string",
        },
        "severity_default": "high",
        "escalation_rules": {
            "days_to_maturity < 30": "critical",
        },
    },
    "interest_rate_reset": {
        "description": "Variable rate debt approaching reset date",
        "title_template": "RATE_RESET: {facility} ({current_rate} -> projected {projected_rate})",
        "required_fields": ["facility", "current_rate", "reset_date"],
        "payload_schema": {
            "facility": "string",
            "lender": "string",
            "current_rate": "string",
            "projected_rate": "string",  # if available
            "reset_date": "string",
            "notional_amount": "string",
            "annual_impact": "string",  # cost impact if rate changes
            "evidence_text": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "annual_impact > 1000000": "high",
        },
    },
    "bank_account_anomaly": {
        "description": "Unusual activity detected in bank account",
        "title_template": "ACCOUNT_ANOMALY: {account} ({anomaly_type}, {amount})",
        "required_fields": ["account", "anomaly_type", "amount"],
        "payload_schema": {
            "account": "string",  # account name/number
            "bank": "string",  # bank name
            "anomaly_type": "string",  # large_transaction, unusual_timing, duplicate
            "amount": "string",  # transaction amount
            "expected_pattern": "string",  # what was expected
            "transaction_date": "string",
            "evidence_text": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "anomaly_type == 'fraud_indicator'": "critical",
        },
    },
}


def generate_signal_title(signal_type: str, payload: dict) -> str:
    """
    Generate deterministic title from signal type and payload.

    Args:
        signal_type: Canonical signal type
        payload: Extracted payload fields

    Returns:
        Formatted title string
    """
    if signal_type not in TREASURY_SIGNAL_TYPES:
        return f"{signal_type.upper()}: Unknown signal type"

    spec = TREASURY_SIGNAL_TYPES[signal_type]
    template = spec.get("title_template", "{signal_type}")

    # Build template variables from payload
    template_vars = {k: str(v) for k, v in payload.items() if v is not None}
    template_vars["signal_type"] = signal_type

    try:
        return template.format(**template_vars)
    except KeyError as e:
        # Missing field - return partial title
        return f"{signal_type.upper()}: (missing {e})"


def get_required_fields(signal_type: str) -> list:
    """Get required payload fields for a signal type."""
    if signal_type not in TREASURY_SIGNAL_TYPES:
        return []
    return TREASURY_SIGNAL_TYPES[signal_type].get("required_fields", [])


def validate_payload(signal_type: str, payload: dict) -> list:
    """
    Validate payload has required fields.

    Returns:
        List of missing field names (empty if valid)
    """
    required = get_required_fields(signal_type)
    return [f for f in required if f not in payload or payload[f] is None]
