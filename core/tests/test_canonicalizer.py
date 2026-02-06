"""
Canonicalizer Unit Tests.

Tests determinism, completeness gating, lookthrough gating,
deduplication, severity assignment, and golden file conformance.

These tests do NOT require a database — the Canonicalizer is a pure function.
"""

import json
import pytest
from pathlib import Path

from core.domain.canonicalizer import (
    CanonicalFlag,
    CanonicalSignal,
    CanonicalStatus,
    CanonicalizationResult,
    canonicalize,
    clear_registry_cache,
    load_constraint_registry,
    _compute_canonical_id,
    _compute_dedupe_key,
    _determine_severity,
    _evaluate_severity_condition,
    _parse_numeric,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear registry cache before each test."""
    clear_registry_cache()
    yield
    clear_registry_cache()


@pytest.fixture
def treasury_registry():
    return load_constraint_registry("treasury")


@pytest.fixture
def wealth_registry():
    return load_constraint_registry("wealth")


def _load_golden(pack: str):
    """Load golden test candidates from eval datasets."""
    path = Path(__file__).parent.parent.parent / "evals" / "datasets" / f"{pack}_canonicalization.json"
    with open(path) as f:
        data = json.load(f)
    return data["candidates"], data["expected"]


# =============================================================================
# Determinism Tests (CRITICAL)
# =============================================================================

class TestCanonicalizerDeterminism:
    """Same inputs must always produce same outputs."""

    @pytest.mark.critical
    def test_same_inputs_same_outputs(self):
        """Run canonicalization twice — results must be identical."""
        candidates = [
            {
                "id": "C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "150", "limit": "100"},
                "confidence": 0.95,
            }
        ]

        result1 = canonicalize(candidates, "treasury")
        result2 = canonicalize(candidates, "treasury")

        assert result1.breach_count == result2.breach_count
        assert result1.observation_count == result2.observation_count
        assert result1.dropped_count == result2.dropped_count
        assert result1.merged_count == result2.merged_count
        assert len(result1.signals) == len(result2.signals)

        for s1, s2 in zip(result1.signals, result2.signals):
            assert s1.canonical_id == s2.canonical_id
            assert s1.canonical_status == s2.canonical_status
            assert s1.severity == s2.severity
            assert s1.title == s2.title
            assert s1.flags == s2.flags
            assert s1.completeness_score == s2.completeness_score
            assert s1.dedupe_key == s2.dedupe_key

    @pytest.mark.critical
    def test_canonical_id_deterministic(self):
        """Canonical ID is SHA256-based and deterministic."""
        id1 = _compute_canonical_id("treasury.position_limit_breach", "position_limit_breach", {"asset": "BTC"})
        id2 = _compute_canonical_id("treasury.position_limit_breach", "position_limit_breach", {"asset": "BTC"})
        assert id1 == id2

        # Different payload → different ID
        id3 = _compute_canonical_id("treasury.position_limit_breach", "position_limit_breach", {"asset": "ETH"})
        assert id1 != id3

    @pytest.mark.critical
    def test_dedupe_key_deterministic(self):
        """Dedupe key is SHA256-based and deterministic."""
        key1 = _compute_dedupe_key("treasury.position_limit_breach", {"asset": "BTC", "entity": "Desk A"}, ["asset"])
        key2 = _compute_dedupe_key("treasury.position_limit_breach", {"asset": "BTC", "entity": "Desk A"}, ["asset"])
        assert key1 == key2

        # Different asset → different key
        key3 = _compute_dedupe_key("treasury.position_limit_breach", {"asset": "ETH", "entity": "Desk A"}, ["asset"])
        assert key1 != key3

        # Extra payload fields don't affect key (only dedupe_keys matter)
        key4 = _compute_dedupe_key("treasury.position_limit_breach", {"asset": "BTC", "entity": "Desk B"}, ["asset"])
        assert key1 == key4


# =============================================================================
# Completeness Gating Tests
# =============================================================================

class TestCompletenessGating:
    """Breach signals must have all required fields."""

    def test_complete_breach_stays_breach(self):
        """All required fields present → breach status."""
        candidates = [{
            "id": "C1",
            "signal_type": "position_limit_breach",
            "payload": {"asset": "BTC", "current_position": "150", "limit": "100"},
            "confidence": 0.95,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.BREACH
        assert CanonicalFlag.COMPLETE in sig.flags
        assert sig.completeness_score == 1.0
        assert sig.missing_fields == []

    def test_incomplete_breach_downgraded_to_observation(self):
        """Missing required field → downgraded to observation."""
        candidates = [{
            "id": "C1",
            "signal_type": "position_limit_breach",
            "payload": {"asset": "BTC", "current_position": "150"},
            "confidence": 0.72,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.DOWNGRADED in sig.flags
        assert "limit" in sig.missing_fields
        assert sig.completeness_score < 1.0

    def test_missing_observation_fields_dropped(self):
        """Missing even observation-level fields → dropped."""
        candidates = [{
            "id": "C1",
            "signal_type": "position_limit_breach",
            "payload": {},
            "confidence": 0.50,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.DROPPED

    def test_unknown_signal_type_dropped(self):
        """Unknown signal type with no constraint → dropped."""
        candidates = [{
            "id": "C1",
            "signal_type": "nonexistent_type",
            "payload": {"foo": "bar"},
            "confidence": 0.60,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.DROPPED
        assert result.dropped_count == 1


# =============================================================================
# Lookthrough Gating Tests
# =============================================================================

class TestLookthroughGating:
    """Constraints requiring lookthrough must be gated."""

    def test_lookthrough_required_without_data_downgraded(self):
        """Concentration breach without lookthrough → downgraded."""
        candidates = [{
            "id": "W1",
            "signal_type": "concentration_breach",
            "payload": {
                "subject": "AAPL",
                "metric": "% of TPV",
                "threshold": "15%",
                "current_value": "22%",
            },
            "confidence": 0.93,
        }]
        result = canonicalize(candidates, "wealth")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.LOOKTHROUGH_REQUIRED in sig.flags
        assert CanonicalFlag.LOOKTHROUGH_MISSING in sig.flags
        assert CanonicalFlag.DOWNGRADED in sig.flags

    def test_lookthrough_required_with_data_stays_breach(self):
        """Concentration breach WITH lookthrough AND authorized threshold → stays breach."""
        candidates = [{
            "id": "W1",
            "signal_type": "concentration_breach",
            "payload": {
                "subject": "AAPL",
                "metric": "% of TPV",
                "threshold": "15%",
                "current_value": "22%",
                "lookthrough_available": True,
                "threshold_authorized": True,  # Required for breach status
            },
            "confidence": 0.93,
        }]
        result = canonicalize(candidates, "wealth")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.BREACH
        assert CanonicalFlag.LOOKTHROUGH_REQUIRED in sig.flags
        assert CanonicalFlag.LOOKTHROUGH_MISSING not in sig.flags


# =============================================================================
# Deduplication Tests
# =============================================================================

class TestDeduplication:
    """Duplicate signals should be merged."""

    def test_same_asset_merged(self):
        """Two position breaches for same asset → one kept, one merged."""
        candidates = [
            {
                "id": "C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "150", "limit": "100"},
                "confidence": 0.95,
            },
            {
                "id": "C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "155", "limit": "100"},
                "confidence": 0.90,
            },
        ]
        result = canonicalize(candidates, "treasury")

        statuses = [s.canonical_status for s in result.signals]
        assert CanonicalStatus.MERGED in statuses
        assert result.merged_count == 1

        # The kept signal should have merged_from
        kept = [s for s in result.signals if s.canonical_status == CanonicalStatus.BREACH]
        assert len(kept) == 1
        assert len(kept[0].merged_from) == 1

    def test_different_asset_not_merged(self):
        """Two position breaches for different assets → both kept."""
        candidates = [
            {
                "id": "C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "150", "limit": "100"},
                "confidence": 0.95,
            },
            {
                "id": "C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "ETH", "current_position": "200", "limit": "150"},
                "confidence": 0.90,
            },
        ]
        result = canonicalize(candidates, "treasury")

        assert result.merged_count == 0
        breaches = [s for s in result.signals if s.canonical_status == CanonicalStatus.BREACH]
        assert len(breaches) == 2

    def test_higher_completeness_kept_on_merge(self):
        """When merging, the signal with higher completeness wins."""
        candidates = [
            {
                "id": "C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "150"},
                "confidence": 0.72,
            },
            {
                "id": "C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "155", "limit": "100", "duration_hours": 36},
                "confidence": 0.90,
            },
        ]
        result = canonicalize(candidates, "treasury")

        # C2 has higher completeness, should be kept
        kept = [s for s in result.signals if s.canonical_status != CanonicalStatus.MERGED]
        assert len(kept) == 1
        assert kept[0].completeness_score > 0.5


# =============================================================================
# Severity Tests
# =============================================================================

class TestSeverityDetermination:
    """Severity must be deterministic from constraint registry rules."""

    def test_default_severity(self):
        """No escalation condition met → default severity."""
        candidates = [{
            "id": "C1",
            "signal_type": "position_limit_breach",
            "payload": {"asset": "BTC", "current_position": "105", "limit": "100", "duration_hours": 2},
            "confidence": 0.95,
        }]
        result = canonicalize(candidates, "treasury")
        assert result.signals[0].severity == "high"

    def test_escalation_triggered(self):
        """Escalation condition met → elevated severity."""
        candidates = [{
            "id": "C1",
            "signal_type": "position_limit_breach",
            "payload": {"asset": "BTC", "current_position": "200", "limit": "100", "duration_hours": 48, "breach_percent": "100"},
            "confidence": 0.95,
        }]
        result = canonicalize(candidates, "treasury")
        assert result.signals[0].severity == "critical"

    def test_covenant_default_critical(self):
        """Covenant breach defaults to critical."""
        candidates = [{
            "id": "C1",
            "signal_type": "covenant_breach",
            "payload": {"covenant_name": "DSCR", "actual_ratio": "1.05", "required_ratio": "1.20"},
            "confidence": 0.88,
        }]
        result = canonicalize(candidates, "treasury")
        assert result.signals[0].severity == "critical"


# =============================================================================
# Severity Condition Parser Tests
# =============================================================================

class TestSeverityConditionParser:
    """The condition evaluator must handle all supported patterns."""

    def test_greater_than(self):
        assert _evaluate_severity_condition("breach_percent > 50", {"breach_percent": "60"})
        assert not _evaluate_severity_condition("breach_percent > 50", {"breach_percent": "40"})

    def test_less_than(self):
        assert _evaluate_severity_condition("current_ratio < 0.10", {"current_ratio": "0.05"})
        assert not _evaluate_severity_condition("current_ratio < 0.10", {"current_ratio": "0.20"})

    def test_equals(self):
        assert _evaluate_severity_condition("failure_reason == 'insufficient_funds'", {"failure_reason": "insufficient_funds"})
        assert not _evaluate_severity_condition("failure_reason == 'insufficient_funds'", {"failure_reason": "other"})

    def test_contains(self):
        assert _evaluate_severity_condition("new_rating contains 'BB'", {"new_rating": "BB+"})
        assert not _evaluate_severity_condition("new_rating contains 'BB'", {"new_rating": "A-"})

    def test_numeric_function(self):
        assert _evaluate_severity_condition("numeric(current_value) > 25", {"current_value": "30%"})
        assert not _evaluate_severity_condition("numeric(current_value) > 25", {"current_value": "20%"})

    def test_missing_field_returns_false(self):
        assert not _evaluate_severity_condition("breach_percent > 50", {})

    def test_empty_condition_returns_false(self):
        assert not _evaluate_severity_condition("", {"breach_percent": "60"})


# =============================================================================
# Numeric Parser Tests
# =============================================================================

class TestNumericParser:
    """Parse numbers from strings with currency/percentage."""

    def test_plain_number(self):
        assert _parse_numeric("42") == 42.0

    def test_negative(self):
        assert _parse_numeric("-28") == -28.0

    def test_percentage(self):
        assert _parse_numeric("22%") == 22.0

    def test_currency(self):
        assert _parse_numeric("$5,000,000") == 5000000.0

    def test_parenthetical_negative(self):
        assert _parse_numeric("(123)") == -123.0

    def test_empty_returns_none(self):
        assert _parse_numeric("") is None

    def test_non_numeric_returns_none(self):
        assert _parse_numeric("hello") is None


# =============================================================================
# Golden File Tests
# =============================================================================

class TestGoldenFileTreasury:
    """Verify canonicalization against golden treasury test cases."""

    def test_treasury_golden_counts(self):
        candidates, expected = _load_golden("treasury")
        result = canonicalize(candidates, "treasury")

        assert result.breach_count == expected["breach_count"]
        assert result.observation_count == expected["observation_count"]
        assert result.dropped_count == expected["dropped_count"]
        assert result.merged_count == expected["merged_count"]
        assert result.downgrade_count == expected["downgrade_count"]

    def test_treasury_golden_signal_statuses(self):
        candidates, expected = _load_golden("treasury")
        result = canonicalize(candidates, "treasury")

        signal_by_source = {s.source_candidate_id: s for s in result.signals}

        # C1: complete breach (BTC, all fields)
        assert signal_by_source["C1"].canonical_status == CanonicalStatus.BREACH
        assert signal_by_source["C1"].severity == "critical"

        # C2: merged into C1 (same dedupe_key: asset=BTC, lower completeness)
        assert signal_by_source["C2"].canonical_status == CanonicalStatus.MERGED

        # C3: merged into C1 (same dedupe_key: asset=BTC)
        assert signal_by_source["C3"].canonical_status == CanonicalStatus.MERGED

        # C4: covenant breach — threshold category + definition_lock gate → OBSERVATION
        assert signal_by_source["C4"].canonical_status == CanonicalStatus.OBSERVATION
        assert signal_by_source["C4"].severity == "critical"
        assert CanonicalFlag.DEFINITION_LOCK_MISSING in signal_by_source["C4"].flags

        # C5: incomplete covenant → observation
        assert signal_by_source["C5"].canonical_status == CanonicalStatus.OBSERVATION

        # C6: settlement_failure — event category → always OBSERVATION
        assert signal_by_source["C6"].canonical_status == CanonicalStatus.OBSERVATION
        assert signal_by_source["C6"].severity == "critical"
        assert CanonicalFlag.EVENT_CATEGORY in signal_by_source["C6"].flags

        # C7: debt_maturity_approaching — event category → always OBSERVATION
        assert signal_by_source["C7"].canonical_status == CanonicalStatus.OBSERVATION
        assert signal_by_source["C7"].severity == "critical"
        assert CanonicalFlag.EVENT_CATEGORY in signal_by_source["C7"].flags

        # C8: complete cash variance — threshold category, all gates pass
        assert signal_by_source["C8"].canonical_status == CanonicalStatus.BREACH
        assert signal_by_source["C8"].severity == "high"

        # C9: missing observation field 'volatility' → dropped
        assert signal_by_source["C9"].canonical_status == CanonicalStatus.DROPPED

        # C10: unknown type → dropped
        assert signal_by_source["C10"].canonical_status == CanonicalStatus.DROPPED


class TestGoldenFileWealth:
    """Verify canonicalization against golden wealth test cases."""

    def test_wealth_golden_lookthrough_gating(self):
        candidates, expected = _load_golden("wealth")
        result = canonicalize(candidates, "wealth")

        # Verify new category-aware counts
        assert result.breach_count == expected["breach_count"]
        assert result.observation_count == expected["observation_count"]
        assert result.dropped_count == expected["dropped_count"]
        assert result.merged_count == expected["merged_count"]
        assert result.downgrade_count == expected["downgrade_count"]

        signal_by_source = {s.source_candidate_id: s for s in result.signals}

        # W1: concentration without lookthrough → observation (AAPL, client-001)
        assert signal_by_source["W1"].canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.LOOKTHROUGH_MISSING in signal_by_source["W1"].flags

        # W2: concentration WITH lookthrough → breach (MSFT, client-006 — different subject/client)
        assert signal_by_source["W2"].canonical_status == CanonicalStatus.BREACH

        # W3: mandate without lookthrough → observation (equity, client-002)
        assert signal_by_source["W3"].canonical_status == CanonicalStatus.OBSERVATION

        # W4: mandate WITH lookthrough → breach (FI duration, client-007 — different constraint/client)
        assert signal_by_source["W4"].canonical_status == CanonicalStatus.BREACH
        assert signal_by_source["W4"].severity == "critical"

    def test_wealth_golden_severity_escalation(self):
        candidates, expected = _load_golden("wealth")
        result = canonicalize(candidates, "wealth")

        signal_by_source = {s.source_candidate_id: s for s in result.signals}

        # W5: suitability drift more_aggressive → critical (threshold, complete)
        assert signal_by_source["W5"].severity == "critical"
        assert signal_by_source["W5"].canonical_status == CanonicalStatus.BREACH

        # W7: fee discrepancy with impact > 10000 → high
        # BUT now threshold + authorized_threshold gate → OBSERVATION
        assert signal_by_source["W7"].severity == "high"
        assert signal_by_source["W7"].canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.AUTHORIZED_THRESHOLD_MISSING in signal_by_source["W7"].flags

        # W8: withdrawal > 50% → critical, but event category → OBSERVATION
        assert signal_by_source["W8"].severity == "critical"
        assert signal_by_source["W8"].canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.EVENT_CATEGORY in signal_by_source["W8"].flags

        # W9: lookthrough_missing — event category → OBSERVATION
        assert signal_by_source["W9"].canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.EVENT_CATEGORY in signal_by_source["W9"].flags


# =============================================================================
# Registry Tests
# =============================================================================

class TestConstraintRegistry:
    """Constraint registry loading and structure."""

    def test_treasury_registry_loads(self, treasury_registry):
        assert len(treasury_registry) == 12
        assert "position_limit_breach" in treasury_registry
        assert "covenant_breach" in treasury_registry

    def test_wealth_registry_loads(self, wealth_registry):
        assert len(wealth_registry) == 12
        assert "concentration_breach" in wealth_registry
        assert "mandate_breach" in wealth_registry

    def test_registry_has_required_fields(self, treasury_registry):
        for signal_type, constraint in treasury_registry.items():
            assert "constraint_id" in constraint, f"{signal_type} missing constraint_id"
            assert "category" in constraint, f"{signal_type} missing category"
            assert "required_for_breach" in constraint, f"{signal_type} missing required_for_breach"
            assert "required_for_observation" in constraint, f"{signal_type} missing required_for_observation"
            assert "severity_rules" in constraint, f"{signal_type} missing severity_rules"
            assert "dedupe_keys" in constraint, f"{signal_type} missing dedupe_keys"

    def test_registry_constraint_ids_match_pattern(self, treasury_registry):
        for signal_type, constraint in treasury_registry.items():
            assert constraint["constraint_id"].startswith("treasury."), f"{signal_type}: bad constraint_id"
            assert constraint["constraint_id"].endswith(signal_type), f"{signal_type}: constraint_id mismatch"

    def test_unknown_pack_returns_empty(self):
        registry = load_constraint_registry("nonexistent")
        assert registry == {}


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_candidates_list(self):
        result = canonicalize([], "treasury")
        assert result.total_candidates == 0
        assert result.breach_count == 0
        assert len(result.signals) == 0

    def test_candidate_with_no_payload(self):
        candidates = [{
            "id": "C1",
            "signal_type": "position_limit_breach",
            "payload": {},
            "confidence": 0.50,
        }]
        result = canonicalize(candidates, "treasury")
        # Should be dropped (missing observation fields)
        assert result.signals[0].canonical_status == CanonicalStatus.DROPPED

    def test_low_confidence_flagged(self):
        candidates = [{
            "id": "C1",
            "signal_type": "settlement_failure",
            "payload": {"counterparty": "X", "amount": "$1M", "failure_reason": "timeout"},
            "confidence": 0.55,
        }]
        result = canonicalize(candidates, "treasury")
        assert CanonicalFlag.LOW_CONFIDENCE in result.signals[0].flags

    def test_title_generation_uses_pack_template(self):
        candidates = [{
            "id": "C1",
            "signal_type": "position_limit_breach",
            "payload": {"asset": "BTC", "current_position": "150", "limit": "100"},
            "confidence": 0.95,
        }]
        result = canonicalize(candidates, "treasury")
        assert "BTC" in result.signals[0].title
        assert "150" in result.signals[0].title
        assert "100" in result.signals[0].title
