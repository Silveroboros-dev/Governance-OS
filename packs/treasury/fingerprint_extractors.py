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
    """Counterparty downgrade: dedupe by counterparty."""
    return {
        "counterparty": payload.get("counterparty"),
    }


def _liquidity_threshold_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Liquidity breach: dedupe by asset."""
    return {
        "asset": payload.get("asset"),
    }


def _fx_exposure_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """FX exposure breach: dedupe by currency pair and direction."""
    return {
        "currency_pair": payload.get("currency_pair"),
        "direction": payload.get("direction"),
    }


def _cash_forecast_variance(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Cash forecast variance: dedupe by account."""
    return {
        "account": payload.get("account"),
    }


def _covenant_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Covenant breach: dedupe by covenant name and facility."""
    return {
        "covenant_name": payload.get("covenant_name"),
        "facility": payload.get("facility"),
    }


def _settlement_failure(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Settlement failure: dedupe by trade ID."""
    return {
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
