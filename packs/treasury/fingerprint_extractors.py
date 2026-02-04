"""
Treasury Pack - Fingerprint Extractors.

Extracts key dimensions from signals for exception fingerprinting.
These dimensions determine whether two exceptions are "the same" for deduplication.
"""

from typing import Dict, Any


def extract_key_dimensions(signal_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key dimensions from a treasury signal for fingerprinting.

    Args:
        signal_type: The signal type
        payload: The signal payload

    Returns:
        Key dimensions dictionary for fingerprint computation
    """
    extractor = EXTRACTORS.get(signal_type, _default_extractor)
    return extractor(payload)


def _position_limit_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Position limit breach: dedupe by asset."""
    return {
        "asset": payload.get("asset"),
    }


def _market_volatility_spike(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Market volatility: dedupe by asset."""
    return {
        "asset": payload.get("asset"),
    }


def _counterparty_credit_downgrade(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Counterparty downgrade: dedupe by counterparty and new rating."""
    return {
        "counterparty": payload.get("counterparty") or payload.get("entity"),
        "new_rating": payload.get("new_rating"),
    }


def _liquidity_threshold_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Liquidity breach: dedupe by entity, threshold name and currency."""
    return {
        "entity": payload.get("entity") or payload.get("account") or payload.get("facility"),
        "threshold_name": payload.get("threshold_name") or payload.get("asset"),
        "currency": payload.get("currency"),
    }


def _fx_exposure_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """FX exposure breach: dedupe by currency pair and direction."""
    return {
        "currency_pair": payload.get("currency_pair"),
        "direction": payload.get("direction"),
    }


def _cash_forecast_variance(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Cash forecast variance: dedupe by entity, account/currency and variance direction."""
    return {
        "entity": payload.get("entity") or payload.get("facility"),
        "account": payload.get("account") or payload.get("currency"),
        "variance_direction": "negative" if payload.get("variance", 0) < 0 else "positive",
    }


def _covenant_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Covenant breach: dedupe by facility/counterparty, covenant name, and required value."""
    return {
        "facility": payload.get("facility") or payload.get("counterparty") or payload.get("bank"),
        "covenant_name": payload.get("covenant_name") or payload.get("covenant_description") or payload.get("covenant_id"),
        "required_value": payload.get("required_value"),
    }


def _settlement_failure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Settlement failure: dedupe by counterparty and trade ID."""
    return {
        "counterparty": payload.get("counterparty"),
        "trade_id": payload.get("trade_id"),
    }


def _default_extractor(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Default: use asset if available, otherwise empty."""
    if "asset" in payload:
        return {"asset": payload["asset"]}
    return {}


# Registry of extractors by signal type
EXTRACTORS = {
    "position_limit_breach": _position_limit_breach,
    "market_volatility_spike": _market_volatility_spike,
    "counterparty_credit_downgrade": _counterparty_credit_downgrade,
    "liquidity_threshold_breach": _liquidity_threshold_breach,
    "fx_exposure_breach": _fx_exposure_breach,
    "cash_forecast_variance": _cash_forecast_variance,
    "covenant_breach": _covenant_breach,
    "settlement_failure": _settlement_failure,
}
