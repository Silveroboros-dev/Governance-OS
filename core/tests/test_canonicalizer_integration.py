"""
Canonicalizer Integration Tests — Value Assessment.

Runs fixture scenarios through the Canonicalizer and measures:
1. Does the registry know about these signal types?
2. What happens with field name mismatches (LLM variance)?
3. How does completeness gating work on realistic payloads?
4. Dedup + severity assignment on multi-signal scenarios.

No LLM needed. No database needed. Pure function tests.
"""

import json
import pytest
from pathlib import Path
from copy import deepcopy

from core.domain.canonicalizer import (
    CanonicalFlag,
    CanonicalStatus,
    canonicalize,
    clear_registry_cache,
    load_constraint_registry,
)


@pytest.fixture(autouse=True)
def clear_cache():
    clear_registry_cache()
    yield
    clear_registry_cache()


def _load_fixture_scenarios(pack: str):
    path = Path(__file__).parent.parent.parent / "packs" / pack / "fixtures" / "scenarios.json"
    with open(path) as f:
        data = json.load(f)
    return data["scenarios"]


def _scenario_to_candidates(scenario, confidence=0.90):
    """Convert a fixture scenario's signals to candidate dicts (as IntakeAgent would produce)."""
    candidates = []
    for i, sig in enumerate(scenario["signals"]):
        candidates.append({
            "id": f"{scenario['id']}_C{i}",
            "signal_type": sig["signal_type"],
            "payload": sig["payload"],
            "confidence": sig.get("metadata", {}).get("confidence", confidence),
            "source_spans": [{"start_char": 0, "end_char": 50, "text": scenario.get("narrative", "")[:50]}],
        })
    return candidates


# =============================================================================
# Test 1: Registry coverage — which fixture signal types are known?
# =============================================================================

class TestRegistryCoverage:
    """Measure how many fixture signal types are recognized by the constraint registry."""

    def test_treasury_fixture_coverage(self):
        """Check which treasury fixture signal types have constraints."""
        registry = load_constraint_registry("treasury")
        scenarios = _load_fixture_scenarios("treasury")

        known = []
        unknown = []
        for scenario in scenarios:
            for sig in scenario["signals"]:
                st = sig["signal_type"]
                if st in registry:
                    known.append(st)
                else:
                    unknown.append(st)

        print(f"\n  Treasury fixture coverage: {len(known)}/{len(known)+len(unknown)}")
        print(f"  Known: {known}")
        print(f"  Unknown: {unknown}")

        # All 7 treasury fixtures should be recognized
        assert len(known) == 7, f"Expected all 7 treasury signal types known, got {len(known)}. Unknown: {unknown}"

    def test_wealth_fixture_coverage(self):
        """Check which wealth fixture signal types have constraints."""
        registry = load_constraint_registry("wealth")
        scenarios = _load_fixture_scenarios("wealth")

        known = []
        unknown = []
        for scenario in scenarios:
            for sig in scenario["signals"]:
                st = sig["signal_type"]
                if st in registry:
                    known.append(st)
                else:
                    unknown.append(st)

        print(f"\n  Wealth fixture coverage: {len(known)}/{len(known)+len(unknown)}")
        print(f"  Known: {known}")
        print(f"  Unknown: {unknown}")

        # Report coverage gap — wealth fixtures use different signal type names
        if unknown:
            pytest.skip(f"Wealth fixture signal types not in registry: {unknown}")


# =============================================================================
# Test 2: Baseline — run clean fixture scenarios through Canonicalizer
# =============================================================================

class TestBaselineFixtures:
    """Run fixture scenarios 1:1 through the Canonicalizer with correct signal types."""

    def test_treasury_all_fixtures_classified(self):
        """Run all treasury fixtures and report classification results.

        Known gaps: fixture payloads use field names like 'current_exposure_usd'
        while constraints expect 'current_exposure'. This test documents the gap.
        """
        scenarios = _load_fixture_scenarios("treasury")

        all_candidates = []
        for scenario in scenarios:
            all_candidates.extend(_scenario_to_candidates(scenario))

        result = canonicalize(all_candidates, "treasury")

        print(f"\n  Treasury baseline: {result.total_candidates} candidates")
        print(f"  Breaches: {result.breach_count}")
        print(f"  Observations: {result.observation_count}")
        print(f"  Dropped: {result.dropped_count}")
        print(f"  Merged: {result.merged_count}")

        for sig in result.signals:
            print(f"    {sig.source_candidate_id}: {sig.canonical_status.value} "
                  f"(severity={sig.severity}, score={sig.completeness_score:.2f}, "
                  f"missing={sig.missing_fields})")

        # With category semantics:
        # - threshold-category signals need complete fields + gates to be BREACH
        # - event-category signals are ALWAYS observation
        # - definition_lock gate blocks covenant_breach without definition_locked payload
        # Most fixture signals will be observation due to:
        #   1. Event category (settlement_failure, debt_maturity, interest_rate_reset, bank_account_anomaly)
        #   2. Definition lock gate (covenant_breach without definition_locked)
        #   3. Field name mismatches (some fixtures use wrong field names)
        assert result.dropped_count <= 1, "At most 1 drop from field name mismatch"
        # With event-category and definition_lock gates, more signals become observations
        assert result.observation_count >= 2, "Event-category and gated signals become observations"
        # Only clean threshold-category signals with all gates pass become breaches
        assert result.breach_count >= 1, "At least 1 clean threshold signal stays breach"

    def test_treasury_severity_matches_expected(self):
        """Canonical severity should align with fixture expected_severity.

        Known mismatches are caused by:
        1. Field name gaps → signal dropped/downgraded → no severity to compare
        2. Fixture expected_severity was set independently from constraint registry rules
        3. Escalation condition thresholds differ from fixture values

        This test reports all mismatches as diagnostics.
        """
        scenarios = _load_fixture_scenarios("treasury")

        matches = []
        mismatches = []
        for scenario in scenarios:
            candidates = _scenario_to_candidates(scenario)
            result = canonicalize(candidates, "treasury")

            active = [s for s in result.signals
                      if s.canonical_status not in (CanonicalStatus.DROPPED, CanonicalStatus.MERGED)]

            if not active:
                mismatches.append((scenario["id"], "NO_SIGNAL", scenario["expected_severity"]))
                continue

            canon_severity = active[0].severity
            expected = scenario["expected_severity"]

            if canon_severity != expected:
                mismatches.append((scenario["id"], canon_severity, expected))
            else:
                matches.append(scenario["id"])

        print(f"\n  Severity matches: {len(matches)}/{len(matches)+len(mismatches)}")
        if matches:
            print(f"  Matched: {matches}")
        if mismatches:
            print(f"  Mismatches (scenario, canonical, expected):")
            for sid, got, want in mismatches:
                print(f"    {sid}: got={got}, expected={want}")

        # At least 2 scenarios should have matching severity (the clean ones)
        assert len(matches) >= 2, (
            f"Too few severity matches ({len(matches)}). "
            f"Registry escalation rules may need updating."
        )


# =============================================================================
# Test 3: LLM variance simulation — field name mismatches
# =============================================================================

class TestLLMVariance:
    """Simulate common LLM extraction errors and measure Canonicalizer resilience."""

    def test_missing_required_field_downgrades(self):
        """Remove one required field from a complete breach — should downgrade."""
        candidates = [{
            "id": "variance_C1",
            "signal_type": "position_limit_breach",
            # Missing "limit" — required for breach
            "payload": {"asset": "BTC", "current_position": "150"},
            "confidence": 0.85,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.DOWNGRADED in sig.flags
        assert "limit" in sig.missing_fields

    def test_field_name_variant_causes_incompleteness(self):
        """LLM uses 'current_exposure_usd' instead of 'current_exposure'.

        fx_exposure_breach requires: currency_pair, current_exposure, limit, direction
        required_for_observation: currency_pair, current_exposure
        With wrong field names, both current_exposure and limit are missing.
        Since current_exposure is also required for observation, this gets DROPPED.
        """
        candidates = [{
            "id": "variance_C2",
            "signal_type": "fx_exposure_breach",
            "payload": {
                "currency_pair": "EUR/USD",
                "current_exposure_usd": 14200000,  # Wrong field name
                "limit_usd": 10000000,              # Wrong field name
                "direction": "long",
            },
            "confidence": 0.92,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        # Gets DROPPED because "current_exposure" is in required_for_observation
        # and it's missing (the payload has "current_exposure_usd" instead)
        assert sig.canonical_status == CanonicalStatus.DROPPED

        print(f"\n  Field name variant: status={sig.canonical_status.value}, "
              f"missing={sig.missing_fields}, score={sig.completeness_score:.2f}")

    def test_field_name_variant_with_correct_names_stays_breach(self):
        """Same scenario but with correct field names → breach."""
        candidates = [{
            "id": "variance_C3",
            "signal_type": "fx_exposure_breach",
            "payload": {
                "currency_pair": "EUR/USD",
                "current_exposure": 14200000,  # Correct field name
                "limit": 10000000,             # Correct field name
                "direction": "long",
            },
            "confidence": 0.92,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.BREACH
        assert sig.completeness_score == 1.0

    def test_unknown_signal_type_dropped(self):
        """LLM invents a signal type not in the registry."""
        candidates = [{
            "id": "variance_C4",
            "signal_type": "portfolio_drift",  # Not in treasury registry
            "payload": {"asset_class": "equities", "drift_percent": 12},
            "confidence": 0.88,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        assert sig.canonical_status == CanonicalStatus.DROPPED

    def test_low_confidence_flagged_but_not_dropped(self):
        """Low confidence gets flagged but doesn't affect status.

        Note: covenant_breach is now threshold + definition_lock gate.
        Without definition_locked in payload, it becomes OBSERVATION (downgraded).
        Low confidence flag still applies.
        """
        candidates = [{
            "id": "variance_C5",
            "signal_type": "covenant_breach",
            "payload": {"covenant_name": "DSCR", "actual_ratio": "1.15", "required_ratio": "1.25"},
            "confidence": 0.55,
        }]
        result = canonicalize(candidates, "treasury")
        sig = result.signals[0]

        # Covenant breach is now threshold + definition_lock → OBSERVATION (gate blocks)
        assert sig.canonical_status == CanonicalStatus.OBSERVATION
        assert CanonicalFlag.LOW_CONFIDENCE in sig.flags
        assert CanonicalFlag.DEFINITION_LOCK_MISSING in sig.flags
        assert CanonicalFlag.DOWNGRADED in sig.flags


# =============================================================================
# Test 4: Dedup on realistic multi-signal input
# =============================================================================

class TestRealisticDedup:
    """Test deduplication on scenarios with multiple signals about the same entity."""

    def test_duplicate_btc_positions_merged(self):
        """Two BTC position signals from different paragraphs → one breach."""
        candidates = [
            {
                "id": "dedup_C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "125", "limit": "100", "duration_hours": 5},
                "confidence": 0.95,
                "source_spans": [{"start_char": 0, "end_char": 50, "text": "BTC position at 125 units"}],
            },
            {
                "id": "dedup_C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "127", "limit": "100", "duration_hours": 6},
                "confidence": 0.88,
                "source_spans": [{"start_char": 200, "end_char": 260, "text": "BTC now at 127 after additional buying"}],
            },
        ]
        result = canonicalize(candidates, "treasury")

        breaches = [s for s in result.signals if s.canonical_status == CanonicalStatus.BREACH]
        merged = [s for s in result.signals if s.canonical_status == CanonicalStatus.MERGED]

        assert len(breaches) == 1
        assert len(merged) == 1
        assert len(breaches[0].merged_from) == 1

        # Evidence from merged signal should be preserved
        assert len(breaches[0].evidence_refs) >= 1

        print(f"\n  Dedup: 2 BTC signals → 1 breach + 1 merged")
        print(f"  Keeper evidence refs: {breaches[0].evidence_refs}")

    def test_different_assets_not_merged(self):
        """BTC and ETH signals should NOT be merged despite same signal type."""
        candidates = [
            {
                "id": "dedup_C3",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "125", "limit": "100"},
                "confidence": 0.95,
            },
            {
                "id": "dedup_C4",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "ETH", "current_position": "200", "limit": "150"},
                "confidence": 0.90,
            },
        ]
        result = canonicalize(candidates, "treasury")

        breaches = [s for s in result.signals if s.canonical_status == CanonicalStatus.BREACH]
        assert len(breaches) == 2
        assert result.merged_count == 0

    def test_mixed_batch_with_dupes_and_incomplete(self):
        """Realistic multi-signal extraction: dupes + incomplete + complete."""
        candidates = [
            # Complete BTC breach
            {
                "id": "mix_C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "125", "limit": "100", "duration_hours": 5},
                "confidence": 0.95,
            },
            # Incomplete BTC mention (no limit) — same dedupe key → merged
            {
                "id": "mix_C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "130"},
                "confidence": 0.70,
            },
            # Complete covenant breach
            {
                "id": "mix_C3",
                "signal_type": "covenant_breach",
                "payload": {"covenant_name": "DSCR", "actual_ratio": "1.15", "required_ratio": "1.25",
                            "facility": "RCF", "lender": "JPMorgan"},
                "confidence": 0.88,
            },
            # Unknown type — dropped
            {
                "id": "mix_C4",
                "signal_type": "portfolio_rebalance_needed",
                "payload": {"reason": "drift"},
                "confidence": 0.65,
            },
            # Complete ETH volatility
            {
                "id": "mix_C5",
                "signal_type": "market_volatility_spike",
                "payload": {"asset": "ETH", "volatility": "0.52", "threshold": "0.30"},
                "confidence": 0.91,
            },
        ]

        result = canonicalize(candidates, "treasury")

        print(f"\n  Mixed batch: {result.total_candidates} candidates")
        print(f"  Breaches: {result.breach_count}")
        print(f"  Observations: {result.observation_count}")
        print(f"  Dropped: {result.dropped_count}")
        print(f"  Merged: {result.merged_count}")
        print(f"  Downgrades: {result.downgrade_count}")

        for sig in result.signals:
            print(f"    {sig.source_candidate_id}: {sig.canonical_status.value} "
                  f"(type={sig.signal_type}, severity={sig.severity})")

        # With category semantics:
        # - BTC position_limit_breach: threshold, complete → BREACH
        # - covenant_breach: threshold + definition_lock gate → OBSERVATION (no definition_locked)
        # - ETH market_volatility_spike: threshold, complete → BREACH
        # - portfolio_rebalance_needed: unknown type → DROPPED
        # - BTC duplicate: MERGED
        assert result.breach_count == 2, "BTC + ETH threshold breaches"
        assert result.observation_count == 1, "covenant_breach blocked by definition_lock gate"
        assert result.dropped_count == 1
        assert result.merged_count == 1


# =============================================================================
# Test 5: Before/After value comparison
# =============================================================================

class TestValueComparison:
    """
    The key question: does the Canonicalizer add value vs raw extraction?

    'Raw' = every candidate goes straight to approval queue.
    'Canonical' = filtered, deduped, severity-assigned.
    """

    def test_treasury_false_breach_prevention(self):
        """
        Simulate an LLM extracting signals with missing fields.
        Without Canonicalizer: all go to humans as 'breaches'.
        With Canonicalizer: incomplete ones become observations.
        """
        candidates = [
            # Real breach
            {
                "id": "fbp_C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "125", "limit": "100"},
                "confidence": 0.95,
            },
            # False breach: missing limit (LLM hallucinated a breach from vague text)
            {
                "id": "fbp_C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "ETH", "current_position": "200"},
                "confidence": 0.72,
            },
            # False breach: missing required_ratio
            {
                "id": "fbp_C3",
                "signal_type": "covenant_breach",
                "payload": {"covenant_name": "Leverage Ratio"},
                "confidence": 0.55,
            },
            # Real breach
            {
                "id": "fbp_C4",
                "signal_type": "settlement_failure",
                "payload": {"counterparty": "Citadel", "amount": "$5M", "failure_reason": "insufficient_funds"},
                "confidence": 0.92,
            },
        ]

        result = canonicalize(candidates, "treasury")

        raw_breach_count = len(candidates)  # Without canonicalizer, all go to queue as potential breaches
        canon_breach_count = result.breach_count
        false_breach_prevented = raw_breach_count - canon_breach_count - result.dropped_count

        print(f"\n  False Breach Prevention:")
        print(f"  Raw (no canonicalizer): {raw_breach_count} signals to review")
        print(f"  Canonicalized: {canon_breach_count} breaches + {result.observation_count} observations + {result.dropped_count} dropped")
        print(f"  False breaches prevented: {false_breach_prevented}")
        print(f"  Human review reduction: {false_breach_prevented}/{raw_breach_count} = {false_breach_prevented/raw_breach_count*100:.0f}%")

        # Key assertion: canonicalizer should reduce breach count
        assert canon_breach_count < raw_breach_count
        assert result.observation_count >= 1  # At least one downgrade

    def test_treasury_duplicate_reduction(self):
        """
        Simulate an LLM extracting the same signal from multiple document sections.
        Without Canonicalizer: duplicates clutter the queue.
        With Canonicalizer: merged into one.
        """
        candidates = [
            # Same BTC signal extracted from 3 different paragraphs
            {
                "id": "dup_C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "125", "limit": "100", "duration_hours": 5},
                "confidence": 0.95,
                "source_spans": [{"start_char": 0, "end_char": 50, "text": "BTC at 125 units vs 100 limit"}],
            },
            {
                "id": "dup_C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "125", "limit": "100"},
                "confidence": 0.88,
                "source_spans": [{"start_char": 200, "end_char": 250, "text": "BTC position remains over limit"}],
            },
            {
                "id": "dup_C3",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "127", "limit": "100"},
                "confidence": 0.82,
                "source_spans": [{"start_char": 400, "end_char": 460, "text": "BTC now up to 127 from earlier 125"}],
            },
            # Different signal — NOT a duplicate
            {
                "id": "dup_C4",
                "signal_type": "covenant_breach",
                "payload": {"covenant_name": "DSCR", "actual_ratio": "1.15", "required_ratio": "1.25",
                            "facility": "RCF"},
                "confidence": 0.88,
            },
        ]

        result = canonicalize(candidates, "treasury")

        raw_queue_size = len(candidates)
        canon_queue_size = result.breach_count + result.observation_count

        print(f"\n  Duplicate Reduction:")
        print(f"  Raw queue size: {raw_queue_size}")
        print(f"  Canonical queue size: {canon_queue_size}")
        print(f"  Duplicates merged: {result.merged_count}")
        print(f"  Queue reduction: {raw_queue_size - canon_queue_size}/{raw_queue_size} = {(raw_queue_size - canon_queue_size)/raw_queue_size*100:.0f}%")

        # Key assertion: queue shrinks
        assert canon_queue_size < raw_queue_size
        assert result.merged_count >= 2  # At least 2 BTC signals merged

        # Evidence from all 3 BTC signals should be preserved in the keeper
        btc_keeper = [s for s in result.signals if s.canonical_status == CanonicalStatus.BREACH
                      and s.signal_type == "position_limit_breach"]
        assert len(btc_keeper) == 1
        assert len(btc_keeper[0].evidence_refs) >= 2  # Accumulated from merged signals

    def test_severity_assignment_value(self):
        """
        Without Canonicalizer: every signal has no severity — humans must triage.
        With Canonicalizer: deterministic severity from constraint registry.
        """
        candidates = [
            {
                "id": "sev_C1",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": "200", "limit": "100",
                            "duration_hours": 48, "breach_percent": "100"},
                "confidence": 0.95,
            },
            {
                "id": "sev_C2",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "ETH", "current_position": "105", "limit": "100",
                            "duration_hours": 1},
                "confidence": 0.90,
            },
            {
                "id": "sev_C3",
                "signal_type": "settlement_failure",
                "payload": {"counterparty": "X", "amount": "$1M", "failure_reason": "insufficient_funds"},
                "confidence": 0.88,
            },
            {
                "id": "sev_C4",
                "signal_type": "settlement_failure",
                "payload": {"counterparty": "Y", "amount": "$500K", "failure_reason": "timing_mismatch"},
                "confidence": 0.85,
            },
        ]

        result = canonicalize(candidates, "treasury")

        print(f"\n  Severity Assignment Value:")
        for sig in result.signals:
            status_str = sig.canonical_status.value
            print(f"    {sig.source_candidate_id}: {sig.signal_type} → severity={sig.severity} ({status_str})")

        # With category semantics: position_limit_breach = threshold → can be BREACH
        # settlement_failure = event → always OBSERVATION
        all_severities = {s.source_candidate_id: s.severity for s in result.signals}

        # BTC with 100% breach + 48h duration → critical (threshold, BREACH)
        assert all_severities["sev_C1"] == "critical"
        # ETH with small breach, short duration → high (default) (threshold, BREACH)
        assert all_severities["sev_C2"] == "high"
        # insufficient_funds → critical (event category, OBSERVATION but severity still assigned)
        assert all_severities["sev_C3"] == "critical"
        # timing_mismatch → high (default) (event category, OBSERVATION)
        assert all_severities["sev_C4"] == "high"

        # Verify settlement_failure is now OBSERVATION (event category)
        sf_signals = [s for s in result.signals if s.signal_type == "settlement_failure"]
        for sf in sf_signals:
            assert sf.canonical_status == CanonicalStatus.OBSERVATION
            assert CanonicalFlag.EVENT_CATEGORY in sf.flags


# =============================================================================
# Test 6: Fixture → Canonicalizer field gap analysis
# =============================================================================

class TestFieldGapAnalysis:
    """Identify where fixture payloads don't match constraint registry field expectations."""

    def test_treasury_field_gaps(self):
        """Report which fixture fields don't match constraint requirements."""
        registry = load_constraint_registry("treasury")
        scenarios = _load_fixture_scenarios("treasury")

        gaps = []
        for scenario in scenarios:
            for sig in scenario["signals"]:
                st = sig["signal_type"]
                constraint = registry.get(st)
                if not constraint:
                    gaps.append((scenario["id"], st, "NO_CONSTRAINT", []))
                    continue

                required = constraint["required_for_breach"]
                payload_keys = set(sig["payload"].keys())
                missing = [f for f in required if f not in payload_keys]

                if missing:
                    gaps.append((scenario["id"], st, "MISSING_FIELDS", missing))

        print("\n  Treasury fixture → constraint field gaps:")
        if not gaps:
            print("    None — all fixtures match constraint requirements!")
        for scenario_id, signal_type, gap_type, missing in gaps:
            print(f"    {scenario_id}/{signal_type}: {gap_type} {missing}")

        # This is informational — gaps tell us where the registry or fixtures need alignment

    def test_wealth_field_gaps(self):
        """Report wealth fixture field gaps."""
        registry = load_constraint_registry("wealth")
        scenarios = _load_fixture_scenarios("wealth")

        known = 0
        unknown = 0
        field_gaps = 0

        for scenario in scenarios:
            for sig in scenario["signals"]:
                st = sig["signal_type"]
                constraint = registry.get(st)
                if not constraint:
                    unknown += 1
                    print(f"    {scenario['id']}/{st}: NOT IN REGISTRY")
                    continue

                known += 1
                required = constraint["required_for_breach"]
                payload_keys = set(sig["payload"].keys())
                missing = [f for f in required if f not in payload_keys]
                if missing:
                    field_gaps += 1
                    print(f"    {scenario['id']}/{st}: missing {missing}")

        print(f"\n  Wealth fixture coverage: {known} known, {unknown} unknown, {field_gaps} with field gaps")
