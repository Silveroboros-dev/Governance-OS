"""
Wealth Pack - Signal Types.

Defines canonical signal types for wealth management with:
- Required payload fields for deterministic extraction
- Title templates for consistent, auditable naming
- Severity rules for policy evaluation

IMPORTANT: LLM extracts structured facts into payload fields.
Titles are generated deterministically from templates - never LLM-invented.
"""

WEALTH_SIGNAL_TYPES = {
    "concentration_breach": {
        "description": "Single position or sector exceeds concentration limit",
        "title_template": "CONCENTRATION_BREACH: {subject} ({current_value} vs {threshold} limit)",
        "required_fields": ["subject", "metric", "threshold", "current_value"],
        "payload_schema": {
            "subject": "string",  # security name, fund, sector
            "metric": "string",  # % of TPV, % of AUM, etc.
            "threshold": "string",  # limit value with unit
            "current_value": "string",  # actual value with unit
            "client_id": "string",
            "portfolio_id": "string",
            "evidence_text": "string",  # source quote
        },
        "severity_default": "high",
        "escalation_rules": {
            "numeric(current_value) > 25": "critical",
            "numeric(current_value) > 20": "high",
        },
    },
    "lookthrough_missing": {
        "description": "Required lookthrough data unavailable for compliance check",
        "title_template": "LOOKTHROUGH_MISSING: {subject} ({missing_data})",
        "required_fields": ["subject", "rule", "missing_data"],
        "payload_schema": {
            "subject": "string",  # fund, ETF, vehicle name
            "rule": "string",  # regulatory rule requiring lookthrough
            "missing_data": "string",  # what data is missing
            "impact": "string",  # what can't be verified
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "rule contains 'regulatory'": "high",
        },
    },
    "fee_discrepancy": {
        "description": "Charged fee differs from expected fee schedule",
        "title_template": "FEE_DISCREPANCY: {charged} charged vs {expected} expected",
        "required_fields": ["charged", "expected"],
        "payload_schema": {
            "charged": "string",  # actual fee with unit (e.g., "0.35%")
            "expected": "string",  # expected fee with unit
            "fee_type": "string",  # management, custody, trading
            "period": "string",  # billing period
            "amount_impact": "string",  # dollar impact if known
            "missing_doc": "string",  # missing fee schedule reference
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "amount_impact > 10000": "high",
        },
    },
    "settlement_pending_cash": {
        "description": "Pending settlement proceeds included in cash calculations",
        "title_template": "SETTLEMENT_PENDING_CASH: {amount} ({impact})",
        "required_fields": ["amount", "impact"],
        "payload_schema": {
            "amount": "string",  # pending amount with currency
            "impact": "string",  # what calculation is affected
            "settlement_date": "string",
            "value_date": "string",
            "affects_liquidity": "boolean",
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "affects_liquidity == true": "high",
        },
    },
    "suitability_drift": {
        "description": "Portfolio risk profile drifted from client's stated tolerance",
        "title_template": "SUITABILITY_DRIFT: {client} ({current_risk} vs {target_risk} target)",
        "required_fields": ["client", "current_risk", "target_risk"],
        "payload_schema": {
            "client": "string",  # client name/ID
            "current_risk": "string",  # current risk level
            "target_risk": "string",  # target/agreed risk level
            "drift_direction": "string",  # more_aggressive, more_conservative
            "contributing_factors": "string",  # what caused drift
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "high",
        "escalation_rules": {
            "drift_direction == 'more_aggressive'": "critical",
        },
    },
    "mandate_breach": {
        "description": "Investment violates client mandate or IPS constraints",
        "title_template": "MANDATE_BREACH: {constraint} ({current} vs {limit} allowed)",
        "required_fields": ["constraint", "current", "limit"],
        "payload_schema": {
            "constraint": "string",  # what mandate rule
            "current": "string",  # current exposure/value
            "limit": "string",  # mandated limit
            "asset_class": "string",  # affected asset class
            "ips_reference": "string",  # IPS section if known
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "critical",
        "escalation_rules": {},
    },
    "rebalancing_required": {
        "description": "Portfolio allocation drifted beyond rebalancing threshold",
        "title_template": "REBALANCING_REQUIRED: {portfolio} ({max_drift} max drift)",
        "required_fields": ["portfolio", "max_drift"],
        "payload_schema": {
            "portfolio": "string",  # portfolio identifier
            "max_drift": "string",  # largest drift percentage
            "trigger_type": "string",  # threshold, calendar, tax_event
            "days_since_rebalance": "number",
            "asset_classes_affected": "string",
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "days_since_rebalance > 365": "high",
        },
    },
    "tax_harvest_opportunity": {
        "description": "Tax-loss harvesting opportunity identified",
        "title_template": "TAX_HARVEST_OPPORTUNITY: {security} ({unrealized_loss} loss)",
        "required_fields": ["security", "unrealized_loss"],
        "payload_schema": {
            "security": "string",  # security name
            "unrealized_loss": "string",  # loss amount
            "cost_basis": "string",
            "current_value": "string",
            "holding_period": "string",  # short-term, long-term
            "wash_sale_risk": "boolean",
            "estimated_tax_savings": "string",
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "low",
        "escalation_rules": {
            "estimated_tax_savings > 50000": "high",
        },
    },
    "withdrawal_request": {
        "description": "Client withdrawal request requiring review",
        "title_template": "WITHDRAWAL_REQUEST: {client} ({amount}, {percent_of_portfolio})",
        "required_fields": ["client", "amount", "percent_of_portfolio"],
        "payload_schema": {
            "client": "string",
            "amount": "string",  # withdrawal amount with currency
            "percent_of_portfolio": "string",
            "liquidation_required": "boolean",
            "reason": "string",
            "requested_date": "string",
            "client_id": "string",
            "portfolio_id": "string",
        },
        "severity_default": "medium",
        "escalation_rules": {
            "percent_of_portfolio > 25": "high",
            "percent_of_portfolio > 50": "critical",
        },
    },
    "risk_tolerance_change": {
        "description": "Client's risk tolerance has changed",
        "title_template": "RISK_TOLERANCE_CHANGE: {client} ({previous} → {new_tolerance})",
        "required_fields": ["client", "previous", "new_tolerance"],
        "payload_schema": {
            "client": "string",
            "previous": "string",  # previous tolerance level
            "new_tolerance": "string",  # new tolerance level
            "reason": "string",  # reason for change
            "client_id": "string",
        },
        "severity_default": "high",
        "escalation_rules": {},
    },
    "objective_change": {
        "description": "Client's investment objective has changed",
        "title_template": "OBJECTIVE_CHANGE: {client} ({previous} → {new_objective})",
        "required_fields": ["client", "previous", "new_objective"],
        "payload_schema": {
            "client": "string",
            "previous": "string",  # previous objective
            "new_objective": "string",  # new objective
            "reason": "string",
            "client_id": "string",
        },
        "severity_default": "high",
        "escalation_rules": {},
    },
    "compliance_flag": {
        "description": "Potential compliance issue requiring review",
        "title_template": "COMPLIANCE_FLAG: {issue_type} ({subject})",
        "required_fields": ["issue_type", "subject", "regulation"],
        "payload_schema": {
            "issue_type": "string",  # specific compliance concern
            "subject": "string",  # what entity/transaction
            "regulation": "string",  # applicable regulation
            "details": "string",
            "evidence_text": "string",
            "client_id": "string",
        },
        "severity_default": "high",
        "escalation_rules": {},
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
    if signal_type not in WEALTH_SIGNAL_TYPES:
        return f"{signal_type.upper()}: Unknown signal type"

    spec = WEALTH_SIGNAL_TYPES[signal_type]
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
    if signal_type not in WEALTH_SIGNAL_TYPES:
        return []
    return WEALTH_SIGNAL_TYPES[signal_type].get("required_fields", [])


def validate_payload(signal_type: str, payload: dict) -> list:
    """
    Validate payload has required fields.

    Returns:
        List of missing field names (empty if valid)
    """
    required = get_required_fields(signal_type)
    return [f for f in required if f not in payload or payload[f] is None]
