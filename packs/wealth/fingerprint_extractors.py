"""
Wealth Pack - Fingerprint Extractors.

Extracts key dimensions from signals for exception fingerprinting.
These dimensions determine whether two exceptions are "the same" for deduplication.
"""

from typing import Dict, Any


def extract_key_dimensions(signal_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key dimensions from a wealth signal for fingerprinting.

    Args:
        signal_type: The signal type
        payload: The signal payload

    Returns:
        Key dimensions dictionary for fingerprint computation
    """
    extractor = EXTRACTORS.get(signal_type, _default_extractor)
    return extractor(payload)


def _portfolio_drift(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Portfolio drift: dedupe by client + portfolio + asset class."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "asset_class": payload.get("asset_class"),
    }


def _rebalancing_required(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Rebalancing required: dedupe by client + portfolio."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
    }


def _suitability_mismatch(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Suitability mismatch: dedupe by client + portfolio."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
    }


def _concentration_breach(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Concentration breach: dedupe by client + portfolio + security."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "security_id": payload.get("security_id"),
    }


def _tax_loss_harvest_opportunity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Tax loss harvest: dedupe by client + portfolio + security."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "security_id": payload.get("security_id"),
    }


def _client_cash_withdrawal(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Cash withdrawal: dedupe by client + portfolio + requested date."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "requested_date": payload.get("requested_date"),
    }


def _market_correlation_spike(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Correlation spike: dedupe by client + portfolio + benchmark."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "benchmark": payload.get("benchmark"),
    }


def _fee_schedule_change(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Fee change: dedupe by client + portfolio + fee type."""
    return {
        "client_id": payload.get("client_id"),
        "portfolio_id": payload.get("portfolio_id"),
        "fee_type": payload.get("fee_type"),
    }


def _default_extractor(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Default: use client_id and portfolio_id if available."""
    result = {}
    if "client_id" in payload:
        result["client_id"] = payload["client_id"]
    if "portfolio_id" in payload:
        result["portfolio_id"] = payload["portfolio_id"]
    return result


# Registry of extractors by signal type
EXTRACTORS = {
    "portfolio_drift": _portfolio_drift,
    "rebalancing_required": _rebalancing_required,
    "suitability_mismatch": _suitability_mismatch,
    "concentration_breach": _concentration_breach,
    "tax_loss_harvest_opportunity": _tax_loss_harvest_opportunity,
    "client_cash_withdrawal": _client_cash_withdrawal,
    "market_correlation_spike": _market_correlation_spike,
    "fee_schedule_change": _fee_schedule_change,
}
