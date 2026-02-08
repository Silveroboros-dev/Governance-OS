"""
Canonicalizer — Deterministic signal normalization layer.

Sits between LLM extraction (IntakeAgent) and the Approval Queue.
Enforces completeness gating, lookthrough requirements, deterministic
severity assignment, deduplication, and stable title rendering.

This is a PURE FUNCTION layer — no LLM, no I/O, no randomness.
Same inputs always produce same outputs.

Design principle: The LLM extracts facts. The Canonicalizer decides
what those facts mean in governance terms. This absorbs model variance
and ensures cross-model stability.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class CanonicalStatus(str, Enum):
    """Result of canonicalization — what happened to this candidate."""
    BREACH = "breach"           # Complete breach signal, all fields present
    OBSERVATION = "observation"  # Downgraded: missing fields for breach
    DROPPED = "dropped"         # Cannot canonicalize (no signal type match, etc.)
    MERGED = "merged"           # Absorbed into another canonical signal


class CanonicalFlag(str, Enum):
    """Flags attached to canonical signals for downstream consumers."""
    COMPLETE = "complete"                     # All breach fields present
    INCOMPLETE_THRESHOLD = "incomplete_threshold"  # Missing threshold value
    INCOMPLETE_MEASURED = "incomplete_measured"    # Missing measured value
    INCOMPLETE_SUBJECT = "incomplete_subject"      # Missing subject identifier
    LOOKTHROUGH_REQUIRED = "lookthrough_required"  # Needs lookthrough data
    LOOKTHROUGH_MISSING = "lookthrough_missing"    # Lookthrough required but not available
    DEFINITION_LOCK_REQUIRED = "definition_lock_required"  # Definition must be locked (covenant-style)
    DEFINITION_LOCK_MISSING = "definition_lock_missing"    # Definition dispute detected, blocks BREACH
    AUTHORIZED_THRESHOLD_REQUIRED = "authorized_threshold_required"  # Threshold must come from authorized source
    AUTHORIZED_THRESHOLD_MISSING = "authorized_threshold_missing"    # No authorized threshold evidence
    DOWNGRADED = "downgraded"                 # Was threshold candidate, became observation
    LOW_CONFIDENCE = "low_confidence"          # Extraction confidence < 0.7
    EVENT_CATEGORY = "event_category"          # Signal is event category (always observation)


# =============================================================================
# Models
# =============================================================================

class CanonicalSignal(BaseModel):
    """A canonicalized signal — stable across model choices."""

    canonical_id: str = Field(..., description="Deterministic ID: SHA256(constraint_id + subject + value_date_bucket)")
    constraint_id: str = Field(..., description="From constraint registry, e.g. 'treasury.position_limit_breach'")
    signal_type: str = Field(..., description="Original signal type from pack vocabulary")
    canonical_status: CanonicalStatus = Field(..., description="breach, observation, dropped, or merged")

    # Payload (from extraction, unchanged)
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Deterministic fields
    severity: str = Field(..., description="Deterministic severity from constraint registry rules")
    title: str = Field(..., description="Deterministic title from pack template")
    flags: List[CanonicalFlag] = Field(default_factory=list)

    # Completeness tracking
    missing_fields: List[str] = Field(default_factory=list, description="Fields required for breach but absent")
    completeness_score: float = Field(0.0, description="Fraction of breach-required fields present")

    # Provenance
    source_candidate_id: str = Field("", description="Original CandidateSignal ID from extraction")
    confidence: float = Field(0.0, description="Original extraction confidence")
    evidence_refs: List[str] = Field(default_factory=list, description="Source span references")

    # Deduplication
    dedupe_key: str = Field("", description="SHA256 of dedupe dimensions for merge detection")
    merged_from: List[str] = Field(default_factory=list, description="IDs of candidates merged into this signal")


class CanonicalizationResult(BaseModel):
    """Result of running the Canonicalizer on a batch of candidates."""

    pack: str
    canonicalized_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Outputs
    signals: List[CanonicalSignal] = Field(default_factory=list)

    # Metrics (for evaluation harness)
    total_candidates: int = 0
    breach_count: int = 0           # Threshold signals that passed all gates → BREACH
    observation_count: int = 0      # All OBSERVATION signals (events + downgraded thresholds)
    dropped_count: int = 0
    merged_count: int = 0
    downgrade_count: int = 0        # Threshold candidates that became observations
    lookthrough_blocked_count: int = 0  # Blocked by lookthrough requirement
    definition_lock_blocked_count: int = 0  # Blocked by definition lock gate
    authorized_threshold_blocked_count: int = 0  # Blocked by authorized threshold gate

    # Category-aware metrics (prevents "success-by-inflating-breaches")
    event_count: int = 0            # Event-category signals (always OBSERVATION)
    threshold_breach_count: int = 0 # Threshold-category signals that became BREACH
    threshold_observation_count: int = 0  # Threshold-category signals downgraded to OBSERVATION

    @property
    def effective_signal_count(self) -> int:
        """Signals that will go to approval queue (breach + observation)."""
        return self.breach_count + self.observation_count


# =============================================================================
# Constraint Registry Loader
# =============================================================================

_registry_cache: Dict[str, Dict[str, Any]] = {}


def load_constraint_registry(pack: str) -> Dict[str, Any]:
    """
    Load constraint registry for a pack.

    Returns dict mapping signal_type -> constraint definition.
    Cached after first load.
    """
    if pack in _registry_cache:
        return _registry_cache[pack]

    registry_path = Path(__file__).parent.parent.parent / "packs" / pack / "constraints.json"
    if not registry_path.exists():
        _registry_cache[pack] = {}
        return {}

    with open(registry_path, "r") as f:
        data = json.load(f)

    constraints = data.get("constraints", {})
    _registry_cache[pack] = constraints
    return constraints


def clear_registry_cache():
    """Clear the constraint registry cache (for testing)."""
    _registry_cache.clear()


# =============================================================================
# Core Canonicalizer (pure functions)
# =============================================================================

def canonicalize(
    candidates: List[Dict[str, Any]],
    pack: str,
    constraint_registry: Optional[Dict[str, Any]] = None,
) -> CanonicalizationResult:
    """
    Canonicalize a batch of candidate signals.

    This is the main entry point. Pure function: same inputs -> same outputs.

    Args:
        candidates: List of candidate signal dicts from IntakeAgent.
            Each must have: signal_type, payload, confidence, source_spans (optional)
        pack: Pack name (treasury, wealth)
        constraint_registry: Optional override; if None, loads from file.

    Returns:
        CanonicalizationResult with canonical signals + metrics.
    """
    if constraint_registry is None:
        constraint_registry = load_constraint_registry(pack)

    result = CanonicalizationResult(pack=pack, total_candidates=len(candidates))

    # Step 1: Canonicalize each candidate individually
    canonical_signals = []
    for candidate in candidates:
        cs = _canonicalize_single(candidate, pack, constraint_registry)
        canonical_signals.append(cs)

    # Step 2: Deduplicate / merge
    merged_signals = _deduplicate(canonical_signals)

    # Step 3: Collect final signals and compute metrics
    for cs in merged_signals:
        result.signals.append(cs)
        if cs.canonical_status == CanonicalStatus.BREACH:
            result.breach_count += 1
        elif cs.canonical_status == CanonicalStatus.OBSERVATION:
            result.observation_count += 1
        elif cs.canonical_status == CanonicalStatus.DROPPED:
            result.dropped_count += 1
        elif cs.canonical_status == CanonicalStatus.MERGED:
            result.merged_count += 1

    # Count downgrades and gate blocks
    for cs in result.signals:
        if CanonicalFlag.DOWNGRADED in cs.flags:
            result.downgrade_count += 1
        if CanonicalFlag.LOOKTHROUGH_MISSING in cs.flags:
            result.lookthrough_blocked_count += 1
        if CanonicalFlag.DEFINITION_LOCK_MISSING in cs.flags:
            result.definition_lock_blocked_count += 1
        if CanonicalFlag.AUTHORIZED_THRESHOLD_MISSING in cs.flags:
            result.authorized_threshold_blocked_count += 1

        # Category-aware metrics
        if CanonicalFlag.EVENT_CATEGORY in cs.flags:
            result.event_count += 1
        elif cs.canonical_status == CanonicalStatus.BREACH:
            result.threshold_breach_count += 1
        elif cs.canonical_status == CanonicalStatus.OBSERVATION and CanonicalFlag.DOWNGRADED in cs.flags:
            result.threshold_observation_count += 1

    return result


def _canonicalize_single(
    candidate: Dict[str, Any],
    pack: str,
    constraint_registry: Dict[str, Any],
) -> CanonicalSignal:
    """Canonicalize a single candidate signal."""

    signal_type = candidate.get("signal_type", "")
    payload = candidate.get("payload", {})
    confidence = candidate.get("confidence", 0.0)
    candidate_id = candidate.get("id", "")
    source_spans = candidate.get("source_spans", [])
    evidence_refs = [s.get("text", "")[:80] for s in source_spans] if source_spans else []

    # Look up constraint
    constraint = constraint_registry.get(signal_type)
    if constraint is None:
        # No constraint defined for this signal type — drop it
        return CanonicalSignal(
            canonical_id=_compute_canonical_id("unknown", signal_type, payload),
            constraint_id="",
            signal_type=signal_type,
            canonical_status=CanonicalStatus.DROPPED,
            payload=payload,
            severity="low",
            title=f"{signal_type.upper()}: No constraint defined",
            flags=[],
            missing_fields=[],
            completeness_score=0.0,
            source_candidate_id=candidate_id,
            confidence=confidence,
            evidence_refs=evidence_refs,
            dedupe_key="",
        )

    constraint_id = constraint["constraint_id"]
    category = constraint.get("category", "event")

    # Step 1: Completeness check
    required_for_breach = constraint.get("required_for_breach", [])
    required_for_observation = constraint.get("required_for_observation", [])
    missing_for_breach = [f for f in required_for_breach if f not in payload or payload[f] is None]
    missing_for_observation = [f for f in required_for_observation if f not in payload or payload[f] is None]

    total_breach_fields = len(required_for_breach) if required_for_breach else 1
    present_breach_fields = total_breach_fields - len(missing_for_breach)
    completeness_score = present_breach_fields / total_breach_fields

    # Step 2: Flags
    flags: List[CanonicalFlag] = []

    if not missing_for_breach:
        flags.append(CanonicalFlag.COMPLETE)
    else:
        # Check which completeness fields are missing
        completeness_fields = constraint.get("completeness_fields", {})
        for role, field_name in completeness_fields.items():
            if field_name in missing_for_breach:
                flag_name = f"incomplete_{role}"
                flag = _resolve_flag(flag_name)
                if flag:
                    flags.append(flag)

    if confidence < 0.7:
        flags.append(CanonicalFlag.LOW_CONFIDENCE)

    # Step 3: Gate checks (lookthrough, definition lock, authorized threshold)
    requires_lookthrough = constraint.get("requires_lookthrough", False)
    if requires_lookthrough:
        flags.append(CanonicalFlag.LOOKTHROUGH_REQUIRED)
        has_lookthrough = payload.get("lookthrough_available", False)
        if not has_lookthrough:
            flags.append(CanonicalFlag.LOOKTHROUGH_MISSING)

    requires_definition_lock = constraint.get("requires_definition_lock", False)
    if requires_definition_lock:
        flags.append(CanonicalFlag.DEFINITION_LOCK_REQUIRED)
        # Definition is locked if payload explicitly confirms it, OR if no dispute indicators
        has_definition_lock = payload.get("definition_locked", False)
        has_dispute = payload.get("definition_disputed", False)
        if not has_definition_lock or has_dispute:
            flags.append(CanonicalFlag.DEFINITION_LOCK_MISSING)

    requires_authorized_threshold = constraint.get("requires_authorized_threshold", False)
    if requires_authorized_threshold:
        flags.append(CanonicalFlag.AUTHORIZED_THRESHOLD_REQUIRED)
        # Threshold is authorized if evidence_type includes an authoritative source
        evidence_type = payload.get("evidence_type", "")
        authorized_sources = {"term_sheet", "fee_schedule", "contract", "mandate_document", "loan_agreement"}
        has_authorized = evidence_type in authorized_sources or payload.get("threshold_authorized", False)
        if not has_authorized:
            flags.append(CanonicalFlag.AUTHORIZED_THRESHOLD_MISSING)

    # Step 4: Determine canonical status using category→status mapping
    #
    # Category semantics:
    #   "event"     → ALWAYS observation (never breach) — informational signals
    #   "threshold" → BREACH only if complete + ALL gates pass
    #   "blocker"   → ALWAYS observation — blocking conditions requiring action
    #
    if missing_for_observation:
        # Can't even be an observation — missing minimum fields
        canonical_status = CanonicalStatus.DROPPED
    elif category == "event":
        # Event-category signals are ALWAYS observations, never breaches
        canonical_status = CanonicalStatus.OBSERVATION
        flags.append(CanonicalFlag.EVENT_CATEGORY)
    elif category == "blocker":
        # Blocker-category signals are observations requiring action
        canonical_status = CanonicalStatus.OBSERVATION
        flags.append(CanonicalFlag.EVENT_CATEGORY)
    elif category == "threshold":
        # Threshold-category: BREACH only if complete + all gates pass
        gate_blocked = False
        if missing_for_breach:
            gate_blocked = True
        if requires_lookthrough and CanonicalFlag.LOOKTHROUGH_MISSING in flags:
            gate_blocked = True
        if requires_definition_lock and CanonicalFlag.DEFINITION_LOCK_MISSING in flags:
            gate_blocked = True
        if requires_authorized_threshold and CanonicalFlag.AUTHORIZED_THRESHOLD_MISSING in flags:
            gate_blocked = True

        if gate_blocked:
            canonical_status = CanonicalStatus.OBSERVATION
            flags.append(CanonicalFlag.DOWNGRADED)
        else:
            canonical_status = CanonicalStatus.BREACH
    else:
        # Unknown category — treat as observation
        canonical_status = CanonicalStatus.OBSERVATION
        flags.append(CanonicalFlag.DOWNGRADED)

    # Step 5: Deterministic severity from registry
    severity = _determine_severity(constraint, payload)

    # Step 6: Deterministic title from pack template
    title = _generate_title(pack, signal_type, payload)

    # Step 7: Compute dedupe key
    dedupe_keys = constraint.get("dedupe_keys", [])
    dedupe_key = _compute_dedupe_key(constraint_id, payload, dedupe_keys)

    # Step 8: Compute canonical ID
    canonical_id = _compute_canonical_id(constraint_id, signal_type, payload)

    return CanonicalSignal(
        canonical_id=canonical_id,
        constraint_id=constraint_id,
        signal_type=signal_type,
        canonical_status=canonical_status,
        payload=payload,
        severity=severity,
        title=title,
        flags=flags,
        missing_fields=missing_for_breach,
        completeness_score=completeness_score,
        source_candidate_id=candidate_id,
        confidence=confidence,
        evidence_refs=evidence_refs,
        dedupe_key=dedupe_key,
    )


def _status_priority(status: CanonicalStatus) -> int:
    """
    Return priority rank for canonical status in dedupe selection.

    Higher value = higher priority (kept over lower priority).
    BREACH must always win over OBSERVATION to prevent breach suppression.
    """
    return {
        CanonicalStatus.BREACH: 3,
        CanonicalStatus.OBSERVATION: 2,
        CanonicalStatus.DROPPED: 1,
        CanonicalStatus.MERGED: 0,
    }.get(status, 0)


def _deduplicate(signals: List[CanonicalSignal]) -> List[CanonicalSignal]:
    """
    Deduplicate canonical signals by dedupe_key.

    When multiple signals have the same dedupe_key:
    - Keep the one with highest status priority (BREACH > OBSERVATION > DROPPED)
    - Then by completeness_score
    - Then by confidence
    - Mark others as MERGED
    - Track merged_from IDs

    CRITICAL: Status priority comes FIRST to prevent breach suppression.
    A lower-confidence breach must always win over a higher-confidence observation.
    """
    if not signals:
        return signals

    # Group by dedupe_key (skip empty keys and dropped signals)
    groups: Dict[str, List[int]] = {}
    for i, sig in enumerate(signals):
        if sig.dedupe_key and sig.canonical_status != CanonicalStatus.DROPPED:
            groups.setdefault(sig.dedupe_key, []).append(i)

    result = []
    merged_indices = set()

    for dedupe_key, indices in groups.items():
        if len(indices) <= 1:
            continue

        # Sort by: status priority DESC, then completeness_score DESC, then confidence DESC
        # Status priority ensures BREACH always wins over OBSERVATION
        sorted_indices = sorted(
            indices,
            key=lambda i: (
                _status_priority(signals[i].canonical_status),
                signals[i].completeness_score,
                signals[i].confidence
            ),
            reverse=True,
        )

        # Keep the best one, accumulate evidence from merged signals
        keeper_idx = sorted_indices[0]
        merge_ids = []
        for idx in sorted_indices[1:]:
            merged_indices.add(idx)
            merge_ids.append(signals[idx].source_candidate_id or signals[idx].canonical_id)
            # Preserve evidence refs from merged signals
            for ref in signals[idx].evidence_refs:
                if ref not in signals[keeper_idx].evidence_refs:
                    signals[keeper_idx].evidence_refs.append(ref)

        signals[keeper_idx].merged_from = merge_ids

    # Build final list
    for i, sig in enumerate(signals):
        if i in merged_indices:
            sig.canonical_status = CanonicalStatus.MERGED
        result.append(sig)

    return result


# =============================================================================
# Helper functions (all pure)
# =============================================================================

def _resolve_flag(flag_name: str) -> Optional[CanonicalFlag]:
    """Resolve a dynamic flag name to a CanonicalFlag enum, or None."""
    try:
        return CanonicalFlag(flag_name)
    except ValueError:
        return None


def _determine_severity(constraint: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Determine severity from constraint registry rules.

    Uses the default severity and checks escalation rules.
    Escalation rules are evaluated in order; last match wins.
    This is deterministic: same payload + same rules = same severity.
    """
    severity_rules = constraint.get("severity_rules", {})
    severity = severity_rules.get("default", "medium")

    escalation = severity_rules.get("escalation", [])
    for rule in escalation:
        condition = rule.get("condition", "")
        if _evaluate_severity_condition(condition, payload):
            severity = rule.get("severity", severity)

    return severity


def _evaluate_severity_condition(condition: str, payload: Dict[str, Any]) -> bool:
    """
    Evaluate a severity escalation condition against payload.

    Supports simple patterns:
      - "field > value"
      - "field < value"
      - "field == 'value'"
      - "field contains 'value'"
      - "field in ['a','b','c']"
      - "numeric(field) > value"

    This is intentionally limited to keep evaluation deterministic
    and auditable. Complex conditions should be broken into multiple rules.
    """
    condition = condition.strip()
    if not condition:
        return False

    try:
        # numeric(field) > value
        if condition.startswith("numeric("):
            inner = condition[8:]
            field_end = inner.index(")")
            field_name = inner[:field_end].strip()
            rest = inner[field_end + 1:].strip()
            field_val = payload.get(field_name)
            if field_val is None:
                return False
            # Try to parse numeric value from string
            num_val = _parse_numeric(str(field_val))
            if num_val is None:
                return False
            return _evaluate_comparison(num_val, rest)

        # "field contains 'value'"
        if " contains " in condition:
            parts = condition.split(" contains ", 1)
            field_name = parts[0].strip()
            match_val = parts[1].strip().strip("'\"")
            field_val = str(payload.get(field_name, ""))
            return match_val in field_val

        # "field in [...]"
        if " in " in condition and "[" in condition:
            parts = condition.split(" in ", 1)
            field_name = parts[0].strip()
            list_str = parts[1].strip()
            field_val = str(payload.get(field_name, ""))
            # Parse simple list
            items = [item.strip().strip("'\"") for item in list_str.strip("[]").split(",")]
            return field_val in items

        # "field == 'value'" or "field == value"
        if " == " in condition:
            parts = condition.split(" == ", 1)
            field_name = parts[0].strip()
            expected = parts[1].strip().strip("'\"")
            field_val = payload.get(field_name)
            if field_val is None:
                return False
            return str(field_val) == expected

        # "field > value" / "field < value" / "field >= value" / "field <= value"
        for op in [">=", "<=", ">", "<"]:
            if f" {op} " in condition:
                parts = condition.split(f" {op} ", 1)
                field_name = parts[0].strip()
                threshold_str = parts[1].strip()
                field_val = payload.get(field_name)
                if field_val is None:
                    return False
                num_val = _parse_numeric(str(field_val))
                threshold = _parse_numeric(threshold_str)
                if num_val is None or threshold is None:
                    return False
                if op == ">":
                    return num_val > threshold
                elif op == "<":
                    return num_val < threshold
                elif op == ">=":
                    return num_val >= threshold
                elif op == "<=":
                    return num_val <= threshold

    except (ValueError, IndexError, TypeError):
        return False

    return False


def _evaluate_comparison(num_val: float, rest: str) -> bool:
    """Evaluate a comparison like '> 25' against a numeric value."""
    rest = rest.strip()
    for op in [">=", "<=", ">", "<", "=="]:
        if rest.startswith(op):
            threshold_str = rest[len(op):].strip()
            threshold = _parse_numeric(threshold_str)
            if threshold is None:
                return False
            if op == ">":
                return num_val > threshold
            elif op == "<":
                return num_val < threshold
            elif op == ">=":
                return num_val >= threshold
            elif op == "<=":
                return num_val <= threshold
            elif op == "==":
                return num_val == threshold
    return False


def _parse_numeric(val: str) -> Optional[float]:
    """Parse a numeric value from a string, handling currency/percentage suffixes."""
    if not val:
        return None
    # Strip common suffixes/prefixes
    cleaned = val.strip().replace(",", "").replace("$", "").replace("€", "").replace("£", "")
    cleaned = cleaned.rstrip("%").strip()
    # Handle negative in parens: (123) -> -123
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _generate_title(pack: str, signal_type: str, payload: Dict[str, Any]) -> str:
    """
    Generate deterministic title from pack templates.

    Delegates to the pack's generate_signal_title function.
    Falls back to a generic title if pack function not available.
    """
    try:
        if pack == "treasury":
            from packs.treasury.signal_types import generate_signal_title
            return generate_signal_title(signal_type, payload)
        elif pack == "wealth":
            from packs.wealth.signal_types import generate_signal_title
            return generate_signal_title(signal_type, payload)
    except (ImportError, KeyError, ValueError, TypeError):
        pass

    # Fallback: generic title with sanitized payload values
    subject = str(payload.get("asset") or payload.get("subject") or payload.get("entity") or "")
    # Truncate to prevent excessively long titles from untrusted input
    subject = subject[:100]
    return f"{signal_type.upper()}: {subject}".strip(": ")


def _compute_canonical_id(constraint_id: str, signal_type: str, payload: Dict[str, Any]) -> str:
    """
    Compute deterministic canonical ID.

    SHA256 of (constraint_id + signal_type + sorted payload).
    """
    canonical = {
        "constraint_id": constraint_id,
        "signal_type": signal_type,
        "payload": payload,
    }
    json_str = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]


def _compute_dedupe_key(constraint_id: str, payload: Dict[str, Any], dedupe_keys: List[str]) -> str:
    """
    Compute deduplication key from constraint_id + specified payload dimensions.

    Returns empty string if no dedupe_keys specified.
    """
    if not dedupe_keys:
        return ""

    dimensions = {"constraint_id": constraint_id}
    for key in sorted(dedupe_keys):
        dimensions[key] = str(payload.get(key, ""))

    json_str = json.dumps(dimensions, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]
