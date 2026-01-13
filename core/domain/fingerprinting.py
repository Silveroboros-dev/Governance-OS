"""
Deterministic fingerprinting for deduplication and hashing.

This module provides pure functions for generating deterministic hashes:
- Exception fingerprints for deduplication
- Input hashes for evaluation idempotency
- Content hashes for evidence packs

CRITICAL: These functions must be deterministic.
Same inputs MUST produce same output every time.
"""

import hashlib
import json
from typing import Any, Dict, List
from uuid import UUID


def compute_evaluation_input_hash(
    policy_version_id: UUID,
    signal_data: List[Dict[str, Any]]
) -> str:
    """
    Compute deterministic hash for evaluation inputs.

    Used for idempotency: same policy + same signals → same hash.

    Args:
        policy_version_id: UUID of the policy version
        signal_data: List of signal dictionaries (must be sorted externally!)

    Returns:
        SHA256 hash (64-character hex string)

    Example:
        >>> signal_data = [
        ...     {"id": "uuid1", "payload": {"value": 100}},
        ...     {"id": "uuid2", "payload": {"value": 200}}
        ... ]
        >>> hash1 = compute_evaluation_input_hash(policy_id, signal_data)
        >>> hash2 = compute_evaluation_input_hash(policy_id, signal_data)
        >>> assert hash1 == hash2  # Deterministic!
    """
    # Create canonical representation
    canonical = {
        "policy_version_id": str(policy_version_id),
        "signals": signal_data  # Caller must sort!
    }

    # Convert to JSON with sorted keys for determinism
    json_str = json.dumps(canonical, sort_keys=True, separators=(',', ':'))

    # Compute SHA256
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def compute_exception_fingerprint(
    policy_id: UUID,
    exception_type: str,
    key_dimensions: Dict[str, Any]
) -> str:
    """
    Compute deterministic fingerprint for exception deduplication.

    Fingerprints determine exception "sameness":
    - Same fingerprint while exception open = duplicate (don't create)
    - Same fingerprint after resolution = can recur

    Args:
        policy_id: UUID of the policy that raised the exception
        exception_type: Type of exception (e.g., 'position_limit_breach')
        key_dimensions: Critical dimensions that define uniqueness
                       (e.g., {"asset": "BTC"} for position limits)

    Returns:
        SHA256 hash (64-character hex string)

    Example:
        >>> # Two BTC position breaches should have same fingerprint
        >>> fp1 = compute_exception_fingerprint(
        ...     policy_id, "position_limit_breach", {"asset": "BTC"}
        ... )
        >>> fp2 = compute_exception_fingerprint(
        ...     policy_id, "position_limit_breach", {"asset": "BTC"}
        ... )
        >>> assert fp1 == fp2
        >>>
        >>> # ETH breach should have different fingerprint
        >>> fp3 = compute_exception_fingerprint(
        ...     policy_id, "position_limit_breach", {"asset": "ETH"}
        ... )
        >>> assert fp1 != fp3
    """
    # Create canonical representation
    canonical = {
        "policy_id": str(policy_id),
        "exception_type": exception_type,
        "key_dimensions": key_dimensions
    }

    # Convert to JSON with sorted keys for determinism
    json_str = json.dumps(canonical, sort_keys=True, separators=(',', ':'))

    # Compute SHA256
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def compute_content_hash(content: Dict[str, Any]) -> str:
    """
    Compute deterministic hash of JSON content.

    Used for evidence pack integrity verification.

    Args:
        content: Dictionary to hash

    Returns:
        SHA256 hash (64-character hex string)
    """
    # Convert to JSON with sorted keys for determinism
    json_str = json.dumps(content, sort_keys=True, separators=(',', ':'))

    # Compute SHA256
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def normalize_signal_data(signal_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize signal data for deterministic hashing.

    Ensures consistent representation:
    - Converts UUIDs to strings
    - Sorts nested dictionaries
    - Removes non-deterministic fields (e.g., ingested_at)

    Args:
        signal_dict: Raw signal dictionary

    Returns:
        Normalized signal dictionary suitable for hashing
    """
    return {
        "id": str(signal_dict["id"]),
        "signal_type": signal_dict["signal_type"],
        "payload": signal_dict["payload"],
        "source": signal_dict["source"],
        "reliability": signal_dict["reliability"],
        "observed_at": signal_dict["observed_at"].isoformat() if hasattr(signal_dict["observed_at"], "isoformat") else signal_dict["observed_at"]
        # Note: Exclude ingested_at - it's not part of logical signal identity
    }
