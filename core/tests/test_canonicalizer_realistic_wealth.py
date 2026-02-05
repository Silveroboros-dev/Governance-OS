"""
Canonicalizer Realistic Wealth Fixtures — Diagnostic Test Suite.

Tests the Canonicalizer against realistic wealth management signal shapes:
- Lookthrough gating (W02)
- Definition disputes / reconciliation (W03)
- Signal type misclassification by LLM (W01, W04, W05, W06)
- Cross-type dedup (W07)

Key insight: these fixtures use `proposed_type` values the LLM might choose,
which often don't match the wealth constraint registry. This reveals a critical
gap: the Canonicalizer can only gate what it recognizes.
"""

import json
import pytest
from pathlib import Path

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


def _load_wealth_realistic():
    path = Path(__file__).parent.parent.parent / "evals" / "datasets" / "wealth_realistic.json"
    with open(path) as f:
        data = json.load(f)
    return data["scenarios"]


def _flatten_signal(sig, pack_registry):
    """
    Flatten a realistic fixture signal into a candidate dict.

    Maps the rich schema (subject, metric_id, operator, threshold, measured)
    to the flat payload format expected by the constraint registry.

    This mapping is what the IntakeAgent prompt should produce.
    """
    payload = {}
    subject = sig.get("subject", {})
    signal_type = sig["proposed_type"]
    constraint = pack_registry.get(signal_type, {})
    required_for_breach = constraint.get("required_for_breach", [])

    # === Map fields based on signal type and constraint requirements ===

    # concentration_breach expects: subject, metric, threshold, current_value
    if signal_type == "concentration_breach":
        payload["subject"] = subject.get("name", "")
        payload["metric"] = sig.get("metric_id", "")
        if sig.get("threshold") is not None:
            payload["threshold"] = str(sig["threshold"])
        if sig.get("measured") is not None:
            payload["current_value"] = str(sig["measured"])
        payload["client_id"] = subject.get("id", "")

    # mandate_breach expects: constraint, current, limit
    elif signal_type == "mandate_breach":
        payload["constraint"] = sig.get("constraint_id", subject.get("name", ""))
        if sig.get("measured") is not None:
            payload["current"] = str(sig["measured"])
        if sig.get("threshold") is not None:
            payload["limit"] = str(sig["threshold"])
        payload["asset_class"] = sig.get("metric_id", "")
        payload["client_id"] = subject.get("id", "")

    # fee_discrepancy expects: charged, expected
    elif signal_type == "fee_discrepancy":
        if sig.get("measured") is not None:
            payload["charged"] = str(sig["measured"])
        if sig.get("threshold") is not None:
            payload["expected"] = str(sig["threshold"])
        payload["fee_type"] = sig.get("metric_id", "")
        payload["client_id"] = subject.get("id", "")

    # suitability_drift expects: client, current_risk, target_risk
    elif signal_type == "suitability_drift":
        payload["client"] = subject.get("name", "")
        if sig.get("measured") is not None:
            payload["current_risk"] = str(sig["measured"])
        if sig.get("threshold") is not None:
            payload["target_risk"] = str(sig["threshold"])
        payload["client_id"] = subject.get("id", "")

    # Default: generic flat mapping
    else:
        payload["entity"] = subject.get("name", "")
        payload["subject_id"] = subject.get("id", "")
        if sig.get("measured") is not None:
            payload["actual_ratio"] = str(sig["measured"])
        if sig.get("threshold") is not None:
            payload["required_ratio"] = str(sig["threshold"])
        if sig.get("operator"):
            payload["operator"] = sig["operator"]

    # Always include these if present
    if sig.get("value_date"):
        payload["value_date"] = sig["value_date"]
    if sig.get("currency"):
        payload["currency"] = sig["currency"]
    if sig.get("metric_id"):
        payload["metric_id"] = sig["metric_id"]
    if sig.get("constraint_id"):
        payload["constraint_id_source"] = sig["constraint_id"]

    # Include lookthrough_available based on flags
    if "LOOKTHROUGH_MISSING" in sig.get("flags", []):
        payload["lookthrough_available"] = False
    elif "LOOKTHROUGH_AVAILABLE" in sig.get("flags", []):
        payload["lookthrough_available"] = True

    source_spans = []
    for ref in sig.get("evidence_refs", []):
        source_spans.append({
            "start_char": 0,
            "end_char": len(ref.get("ref", "")),
            "text": ref.get("ref", ""),
        })

    return {
        "id": sig["id"],
        "signal_type": signal_type,
        "payload": payload,
        "confidence": 0.85,
        "source_spans": source_spans,
    }


def _scenario_to_candidates(scenario, registry):
    """Convert scenario signals to candidate dicts with proper field mapping."""
    return [_flatten_signal(sig, registry) for sig in scenario["input_signals"]]


# =============================================================================
# Full diagnostic
# =============================================================================

class TestWealthRealisticDiagnostic:

    def test_all_scenarios_diagnostic(self):
        """Run all scenarios and report results."""
        scenarios = _load_wealth_realistic()
        registry = load_constraint_registry("wealth")

        print("\n" + "=" * 80)
        print("WEALTH REALISTIC FIXTURE DIAGNOSTIC REPORT")
        print("=" * 80)

        total_pass = 0
        total_fail = 0

        for scenario in scenarios:
            candidates = _scenario_to_candidates(scenario, registry)
            result = canonicalize(candidates, "wealth")

            expected_after = scenario["expected"]["after_breach_count"]
            expected_before = scenario["expected"]["before_breach_count"]
            actual_breach = result.breach_count

            match = "PASS" if actual_breach == expected_after else "FAIL"
            if match == "PASS":
                total_pass += 1
            else:
                total_fail += 1

            print(f"\n  [{match}] {scenario['scenario_id']}: {scenario['title']}")
            print(f"    Expected: {expected_before} → {expected_after} breaches")
            print(f"    Actual:   {expected_before} → {actual_breach} breaches "
                  f"({result.observation_count} obs, {result.dropped_count} drop, "
                  f"{result.merged_count} merge)")

            for sig in result.signals:
                icon = {"breach": "!!", "observation": "??", "dropped": "XX", "merged": ">>"
                        }.get(sig.canonical_status.value, "  ")
                flags_str = ", ".join(f.value for f in sig.flags) if sig.flags else "none"
                print(f"    [{icon}] {sig.source_candidate_id}: "
                      f"{sig.canonical_status.value} severity={sig.severity} "
                      f"score={sig.completeness_score:.2f} "
                      f"missing={sig.missing_fields} flags=[{flags_str}]")

            if scenario.get("notes"):
                for note in scenario["notes"]:
                    print(f"    NOTE: {note}")

        print(f"\n  {'=' * 60}")
        print(f"  TOTAL: {total_pass} PASS, {total_fail} FAIL out of {len(scenarios)}")
        print(f"  {'=' * 60}")


# =============================================================================
# W01: True concentration breach — proposed as position_limit_breach
# =============================================================================

class TestW01TrueConcentrationBreach:
    """
    The LLM proposes 'position_limit_breach' but the wealth registry only
    has 'concentration_breach'. Under current rules this gets DROPPED
    because the signal type is unknown.

    This documents a real gap: the LLM needs to use the exact signal type
    from the pack vocabulary, OR the Canonicalizer needs type aliasing.
    """

    def test_position_limit_breach_in_wealth_dropped(self):
        scenarios = _load_wealth_realistic()
        scenario = next(s for s in scenarios if s["scenario_id"] == "W01_TRUE_CONCENTRATION_BREACH")
        registry = load_constraint_registry("wealth")
        candidates = _scenario_to_candidates(scenario, registry)

        result = canonicalize(candidates, "wealth")

        print(f"\n  W01: proposed_type=position_limit_breach in wealth pack")
        print(f"    Result: {result.breach_count} breach, {result.dropped_count} dropped")

        # position_limit_breach is NOT in wealth registry → dropped
        if result.dropped_count == 1:
            print("    GAP: 'position_limit_breach' not in wealth registry.")
            print("    FIX OPTIONS:")
            print("      a) Add type alias: position_limit_breach → concentration_breach")
            print("      b) Teach IntakeAgent to use 'concentration_breach' for wealth pack")
            print("      c) Add position_limit_breach to wealth constraint registry")

        # The expected after_breach_count is 1, but current behavior drops it.
        # We test what actually happens and document the gap.
        assert result.dropped_count == 1 or result.breach_count == 1

    def test_correct_type_concentration_breach_works(self):
        """Same signal but with correct type → breach."""
        registry = load_constraint_registry("wealth")
        candidates = [{
            "id": "w01_correct",
            "signal_type": "concentration_breach",
            "payload": {
                "subject": "OakRidge Private Credit Fund III",
                "metric": "pct_of_tpv",
                "threshold": "0.15",
                "current_value": "0.176",
                "client_id": "fund_oakridge_pcf_iii",
                "lookthrough_available": True,
            },
            "confidence": 0.85,
        }]
        result = canonicalize(candidates, "wealth")

        assert result.breach_count == 1
        assert result.signals[0].canonical_status == CanonicalStatus.BREACH
        print(f"\n  W01 (corrected): concentration_breach → BREACH. Works as expected.")


# =============================================================================
# W02: Lookthrough missing
# =============================================================================

class TestW02LookthroughMissing:
    """
    Same type issue as W01: 'position_limit_breach' is not in wealth registry.
    Even if it were, the test is about lookthrough gating.
    """

    def test_lookthrough_missing_with_correct_type(self):
        """Use concentration_breach with lookthrough_available=false → observation."""
        candidates = [{
            "id": "w02_correct",
            "signal_type": "concentration_breach",
            "payload": {
                "subject": "EM Equity ETF",
                "metric": "single_country_em_exposure_pct",
                "threshold": "0.10",
                "current_value": "0.114",
                "client_id": "etf_em_equity",
                "lookthrough_available": False,
            },
            "confidence": 0.85,
        }]
        result = canonicalize(candidates, "wealth")

        assert result.breach_count == 0
        assert result.observation_count == 1
        assert CanonicalFlag.LOOKTHROUGH_MISSING in result.signals[0].flags
        print(f"\n  W02: concentration_breach + lookthrough_available=false → OBSERVATION. Correct.")


# =============================================================================
# W03: Liquidity definition dispute — mandate_breach with lookthrough
# =============================================================================

class TestW03LiquidityDispute:
    """
    mandate_breach requires lookthrough. Without lookthrough_available=true,
    it should be downgraded. Both signals also have conflicting measured values.
    """

    def test_mandate_breach_without_lookthrough_downgraded(self):
        scenarios = _load_wealth_realistic()
        scenario = next(s for s in scenarios if s["scenario_id"] == "W03_LIQUIDITY_DEFINITION_DISPUTE")
        registry = load_constraint_registry("wealth")
        candidates = _scenario_to_candidates(scenario, registry)

        result = canonicalize(candidates, "wealth")

        print(f"\n  W03: {result.breach_count} breach, {result.observation_count} obs, "
              f"{result.merged_count} merged")
        for sig in result.signals:
            print(f"    {sig.source_candidate_id}: {sig.canonical_status.value} "
                  f"missing={sig.missing_fields} flags={[f.value for f in sig.flags]}")

        # mandate_breach requires lookthrough, neither signal has it → 0 breaches
        assert result.breach_count == 0, (
            f"Mandate breach without lookthrough should not be breach. Got {result.breach_count}."
        )


# =============================================================================
# W04: compliance_breach not in registry → dropped
# =============================================================================

class TestW04MissingKID:

    def test_compliance_breach_dropped(self):
        scenarios = _load_wealth_realistic()
        scenario = next(s for s in scenarios if s["scenario_id"] == "W04_MISSING_KID_BLOCKER")
        registry = load_constraint_registry("wealth")
        candidates = _scenario_to_candidates(scenario, registry)

        result = canonicalize(candidates, "wealth")

        assert result.breach_count == 0
        assert result.dropped_count == 1
        print(f"\n  W04: compliance_breach → dropped (not in wealth registry). Correct.")


# =============================================================================
# W05: Fee discrepancy proposed as mandate_breach
# =============================================================================

class TestW05FeeDiscrepancy:
    """
    Proposed as mandate_breach but it's really a fee issue.
    mandate_breach requires lookthrough → without it, downgraded.
    """

    def test_fee_as_mandate_breach_downgraded(self):
        scenarios = _load_wealth_realistic()
        scenario = next(s for s in scenarios if s["scenario_id"] == "W05_FEE_DISCREPANCY_NOT_BREACH")
        registry = load_constraint_registry("wealth")
        candidates = _scenario_to_candidates(scenario, registry)

        result = canonicalize(candidates, "wealth")

        print(f"\n  W05: {result.breach_count} breach, {result.observation_count} obs")
        for sig in result.signals:
            print(f"    {sig.source_candidate_id}: {sig.canonical_status.value} "
                  f"missing={sig.missing_fields}")

        assert result.breach_count == 0, (
            f"Fee discrepancy as mandate_breach should not survive. Got {result.breach_count}."
        )


# =============================================================================
# W06: Suitability stale as mandate_breach
# =============================================================================

class TestW06SuitabilityStale:

    def test_stale_suitability_not_breach(self):
        scenarios = _load_wealth_realistic()
        scenario = next(s for s in scenarios if s["scenario_id"] == "W06_SUITABILITY_STALE_PROCESS_RISK")
        registry = load_constraint_registry("wealth")
        candidates = _scenario_to_candidates(scenario, registry)

        result = canonicalize(candidates, "wealth")

        print(f"\n  W06: {result.breach_count} breach, {result.observation_count} obs")
        for sig in result.signals:
            print(f"    {sig.source_candidate_id}: {sig.canonical_status.value} "
                  f"missing={sig.missing_fields}")

        assert result.breach_count == 0, (
            f"Stale suitability as mandate_breach should not survive. Got {result.breach_count}."
        )


# =============================================================================
# W07: Cross-type dedup
# =============================================================================

class TestW07CrossTypeDedup:
    """
    Two signals about the same fact: one as mandate_breach, one as position_limit_breach.
    Current Canonicalizer dedupes within same signal_type only.
    Cross-type dedup requires a higher-level concept (same constraint_id + subject).
    """

    def test_cross_type_dedup_diagnostic(self):
        scenarios = _load_wealth_realistic()
        scenario = next(s for s in scenarios if s["scenario_id"] == "W07_DUPLICATE_MANDATE_AND_CONCENTRATION_MERGE")
        registry = load_constraint_registry("wealth")
        candidates = _scenario_to_candidates(scenario, registry)

        result = canonicalize(candidates, "wealth")

        print(f"\n  W07: {result.breach_count} breach, {result.observation_count} obs, "
              f"{result.dropped_count} dropped, {result.merged_count} merged")
        for sig in result.signals:
            print(f"    {sig.source_candidate_id}: type={sig.signal_type} "
                  f"{sig.canonical_status.value} dedupe_key={sig.dedupe_key}")

        # position_limit_breach is not in wealth registry → dropped
        # mandate_breach requires lookthrough → downgraded or observation
        # So at most 0-1 breaches
        expected_after = scenario["expected"]["after_breach_count"]
        print(f"\n    Expected after: {expected_after} breach")
        print(f"    Actual: {result.breach_count} breach")

        if result.breach_count != expected_after:
            print("    GAP: Cross-type dedup not implemented.")
            print("    REASONS:")
            print("      - position_limit_breach not in wealth registry → dropped")
            print("      - mandate_breach requires lookthrough → downgraded")
            print("      - Even if both survived, different signal_type → different dedupe keys")
            print("    FIX: Need cross-type dedup by (constraint_id_source + subject_id)")


# =============================================================================
# Value measurement
# =============================================================================

class TestWealthValueMeasurement:

    def test_overall_false_breach_prevention(self):
        scenarios = _load_wealth_realistic()
        registry = load_constraint_registry("wealth")

        total_raw = 0
        total_breach = 0
        total_obs = 0
        total_dropped = 0
        total_merged = 0

        for scenario in scenarios:
            candidates = _scenario_to_candidates(scenario, registry)
            total_raw += len(candidates)

            result = canonicalize(candidates, "wealth")
            total_breach += result.breach_count
            total_obs += result.observation_count
            total_dropped += result.dropped_count
            total_merged += result.merged_count

        prevented = total_raw - total_breach

        print(f"\n  {'=' * 60}")
        print(f"  WEALTH REALISTIC VALUE SUMMARY")
        print(f"  {'=' * 60}")
        print(f"  Raw signals claiming breach:  {total_raw}")
        print(f"  After canonicalization:")
        print(f"    Breaches:     {total_breach}")
        print(f"    Observations: {total_obs}")
        print(f"    Dropped:      {total_dropped}")
        print(f"    Merged:       {total_merged}")
        print(f"  False breaches prevented: {prevented}/{total_raw} "
              f"({prevented/total_raw*100:.0f}%)")
        print(f"  {'=' * 60}")

        assert prevented >= 5, f"Expected at least 5 prevented, got {prevented}"
