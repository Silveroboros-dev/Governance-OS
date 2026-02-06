"""
End-to-End Test: Meridian Wealth — Stonebridge Family Office Pack V2

Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer → Results

Expected signals from the document (section 7):
1. issuer_cap_breach (BREACH): Alpina Energy ~8.4% > 7.0% (authorized threshold in IPS)
2. mandate_breach / equity_max (OBSERVATION): 42.1% > 40% but classification dispute
3. concentration_breach / fund_cap (OBSERVATION): ETF 12.7% > 12% but needs look-through
4. withdrawal_request (OBSERVATION): CHF 500k by 2026-03-12
5. settlement_pending_cash (OBSERVATION): CHF 220k pending
6. compliance_flag / missing_kid (OBSERVATION): ZEN Autocall + possibly Eiger Certificate
7. fee_discrepancy (BREACH): 0.45% invoiced vs 0.30% signed (authorized threshold present)
8. suitability_stale (OBSERVATION): 2024-09-15 questionnaire

Key test targets:
- Issuer cap: authorized threshold PRESENT in IPS → should allow BREACH
- Fee discrepancy: authorized threshold PRESENT (signed schedule) → should allow BREACH
- Equity max: classification dispute → should gate to OBSERVATION
- Fund concentration: look-through required → should gate to OBSERVATION
- Events (withdrawal, settlement, missing KID, stale suitability) → must remain OBSERVATION
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.domain.canonicalizer import (
    CanonicalFlag,
    CanonicalStatus,
    canonicalize,
    clear_registry_cache,
)


def load_document() -> str:
    """Load the Stonebridge wealth pack document."""
    doc_path = Path(__file__).parent / "datasets" / "wealth_e2e_stonebridge.txt"
    return doc_path.read_text()


def run_intake_agent(document_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Run IntakeAgent to extract candidate signals from document.

    Returns raw extraction result for analysis.
    """
    from coprocessor.agents.intake_agent import IntakeAgent

    agent = IntakeAgent(
        api_key=api_key,
        use_cache=False,      # Skip cache for testing
        use_thinking=True,     # Enable thinking for audit transparency
        thinking_budget=8192,
    )

    result = agent.extract_signals_sync(
        content=document_text,
        pack="wealth",
        document_source="evals/datasets/wealth_e2e_stonebridge.txt",
        document_metadata={
            "client": "Stonebridge Family Office",
            "mandate": "Discretionary (Balanced)",
            "created": "2026-03-03",
            "type": "wealth_management_pack",
        },
    )

    return result


def extraction_to_candidate_dicts(result) -> List[Dict[str, Any]]:
    """Convert ExtractionResult candidates to dicts for Canonicalizer."""
    candidates = []
    for i, candidate in enumerate(result.candidates):
        candidates.append({
            "id": f"W{i}",
            "signal_type": candidate.signal_type,
            "payload": candidate.payload,
            "confidence": candidate.confidence,
            "source_spans": [
                {
                    "start_char": span.start_char,
                    "end_char": span.end_char,
                    "text": span.text,
                }
                for span in candidate.source_spans
            ],
        })
    return candidates


# =============================================================================
# Expected signal taxonomy from the document
# =============================================================================

EXPECTED_SIGNALS = {
    "issuer_cap_breach": {
        "description": "Alpina Energy ~8.4% > 7.0% issuer cap",
        "should_extract": True,
        "expected_canon_status": "breach",  # authorized threshold in IPS excerpt
        "reason": "IPS clearly states 7% issuer cap; both PMS and custodian confirm ~8.4%",
        "alt_types": ["concentration_breach", "position_limit_breach"],
    },
    "fee_discrepancy": {
        "description": "Custody fee 0.45% invoiced vs 0.30% signed schedule",
        "should_extract": True,
        "expected_canon_status": "breach",  # authorized threshold (signed schedule) present
        "reason": "Signed fee schedule excerpt provides authorized threshold evidence",
    },
    "mandate_breach_equity": {
        "description": "Equity exposure 42.1% > 40% hard max",
        "should_extract": True,
        "expected_canon_status": "observation",  # classification dispute gates this
        "reason": "Classification dispute (Eiger certificate equity vs structured) makes breach uncertain",
        "alt_types": ["mandate_breach"],
    },
    "concentration_breach_fund": {
        "description": "Global Equity ETF 12.7% > 12% fund cap",
        "should_extract": True,
        "expected_canon_status": "observation",  # requires look-through
        "reason": "Fund concentration requires look-through per registry; constituents missing",
        "alt_types": ["concentration_breach"],
    },
    "withdrawal_request": {
        "description": "CHF 500k by 2026-03-12",
        "should_extract": True,
        "expected_canon_status": "observation",  # event category
        "reason": "Withdrawal request is an event, not threshold breach",
    },
    "settlement_pending_cash": {
        "description": "CHF 220k pending settlement",
        "should_extract": "maybe",
        "expected_canon_status": "observation",  # event category
        "reason": "Pending settlement affects liquidity but is informational",
    },
    "compliance_flag_kid": {
        "description": "Missing KID for ZEN Autocall (and possibly Eiger)",
        "should_extract": True,
        "expected_canon_status": "observation",  # blocker category
        "reason": "Missing KID is a product governance blocker, not a threshold breach",
        "alt_types": ["compliance_flag", "missing_kid"],
    },
    "suitability_stale": {
        "description": "Suitability questionnaire from 2024-09-15 (>12 months)",
        "should_extract": "maybe",
        "expected_canon_status": "observation",  # event category
        "reason": "Stale suitability is governance issue, not threshold breach",
        "alt_types": ["compliance_flag", "suitability_drift"],
    },
}


def print_header(title: str):
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


def print_section(title: str):
    print(f"\n  --- {title} ---")


def analyze_results(
    extraction_result,
    canon_result,
    candidate_dicts: List[Dict[str, Any]],
):
    """Analyze and report on e2e results."""

    print_header("E2E RESULTS: Meridian Wealth — Stonebridge Family Office V2")

    # ── Phase 1: IntakeAgent Extraction ──
    print_section("PHASE 1: IntakeAgent Extraction (Gemini 3)")
    print(f"  Total candidates extracted: {extraction_result.total_candidates}")
    print(f"  High confidence (>=0.9):    {extraction_result.high_confidence_count}")
    print(f"  Needs verification (<0.7):  {extraction_result.requires_verification_count}")

    if extraction_result.extraction_notes:
        print(f"\n  Extraction notes:")
        for line in extraction_result.extraction_notes.split("\n"):
            if line.strip():
                print(f"    {line.strip()}")

    if extraction_result.thinking_summary:
        print(f"\n  Thinking summary (first 600 chars):")
        summary = extraction_result.thinking_summary[:600]
        for line in summary.split("\n"):
            print(f"    {line}")
        if len(extraction_result.thinking_summary) > 600:
            print(f"    ... ({len(extraction_result.thinking_summary)} total chars)")

    # List all extracted candidates
    print(f"\n  Extracted candidates:")
    type_counts = {}
    for i, c in enumerate(extraction_result.candidates):
        conf_icon = "●" if c.confidence >= 0.9 else "◐" if c.confidence >= 0.7 else "○"
        print(f"    [{conf_icon}] W{i}: {c.signal_type} (conf={c.confidence:.2f})")
        # Show key payload fields
        for key in ["subject", "constraint", "current", "limit", "threshold",
                     "current_value", "client", "amount", "charged", "expected",
                     "issue_type", "regulation", "metric"]:
            if key in c.payload and c.payload[key]:
                print(f"         {key}: {c.payload[key]}")
        # Show first source span
        if c.source_spans:
            span_text = c.source_spans[0].text[:80]
            print(f"         evidence: \"{span_text}...\"" if len(c.source_spans[0].text) > 80
                  else f"         evidence: \"{span_text}\"")

        type_counts[c.signal_type] = type_counts.get(c.signal_type, 0) + 1

    print(f"\n  Signal type distribution:")
    for st, count in sorted(type_counts.items()):
        print(f"    {st}: {count}")

    # ── Phase 2: Canonicalizer ──
    print_section("PHASE 2: Canonicalizer")
    print(f"  Breaches:      {canon_result.breach_count}")
    print(f"  Observations:  {canon_result.observation_count}")
    print(f"  Dropped:       {canon_result.dropped_count}")
    print(f"  Merged:        {canon_result.merged_count}")

    print(f"\n  Canonical signals:")
    for sig in canon_result.signals:
        status_icon = {
            "breach": "!!",
            "observation": "??",
            "dropped": "XX",
            "merged": ">>",
        }.get(sig.canonical_status.value, "  ")

        flags_str = ", ".join(f.value for f in sig.flags) if sig.flags else "none"
        print(f"    [{status_icon}] {sig.source_candidate_id}: "
              f"{sig.canonical_status.value} | severity={sig.severity} | "
              f"score={sig.completeness_score:.2f}")
        print(f"         type={sig.signal_type} | missing={sig.missing_fields}")
        print(f"         flags=[{flags_str}]")
        if sig.title:
            print(f"         title: {sig.title}")
        if sig.merged_from:
            print(f"         merged_from: {sig.merged_from}")

    # ── Phase 3: Expected vs Actual ──
    print_section("PHASE 3: Expected vs Actual Comparison")

    extracted_types = set(c.signal_type for c in extraction_result.candidates)
    canonical_types = {}
    for sig in canon_result.signals:
        if sig.canonical_status != CanonicalStatus.MERGED:
            if sig.signal_type not in canonical_types:
                canonical_types[sig.signal_type] = []
            canonical_types[sig.signal_type].append(sig)

    for expected_type, spec in EXPECTED_SIGNALS.items():
        # Check for main type or alternatives
        alt_types = spec.get("alt_types", [])
        all_types = [expected_type] + alt_types

        extracted = any(t in extracted_types for t in all_types)
        matched_type = next((t for t in all_types if t in extracted_types), None)

        canon_signals = []
        for t in all_types:
            canon_signals.extend(canonical_types.get(t, []))

        should = spec["should_extract"]
        if should == True:
            extract_result = "PASS" if extracted else "MISS"
        elif should == "maybe":
            extract_result = "FOUND" if extracted else "SKIP"
        else:
            extract_result = "OK" if not extracted else "UNEXPECTED"

        canon_statuses = [s.canonical_status.value for s in canon_signals]

        print(f"\n    {expected_type}:")
        print(f"      Expected: {spec['description']}")
        print(f"      Extracted: [{extract_result}] (should={should})")
        if matched_type and matched_type != expected_type:
            print(f"      Matched as: {matched_type}")
        print(f"      After canon: {canon_statuses if canon_statuses else 'not present'}")
        if spec.get("expected_canon_status") != "any" and canon_signals:
            match = any(s.canonical_status.value == spec["expected_canon_status"] for s in canon_signals)
            print(f"      Status match: {'YES' if match else 'NO'} "
                  f"(expected {spec['expected_canon_status']})")
        print(f"      Reason: {spec['reason']}")

    # ── Phase 4: Value Assessment ──
    print_section("PHASE 4: Value Assessment")

    total_raw = len(extraction_result.candidates)
    breaches_after = canon_result.breach_count
    observations_after = canon_result.observation_count
    dropped_after = canon_result.dropped_count
    merged_after = canon_result.merged_count

    false_breach_prevented = total_raw - breaches_after

    print(f"  Raw LLM signals:           {total_raw}")
    print(f"  → Breaches (threshold):    {breaches_after}")
    print(f"  → Observations:            {observations_after}")
    if observations_after > 0:
        print(f"    - Events (always obs):   {canon_result.event_count}")
        print(f"    - Downgraded thresholds: {observations_after - canon_result.event_count}")
    print(f"  → Dropped (invalid type):  {dropped_after}")
    print(f"  → Merged (deduped):        {merged_after}")
    if total_raw > 0:
        print(f"  False breach prevention:   {false_breach_prevented}/{total_raw} "
              f"({false_breach_prevented/total_raw*100:.0f}%)")
    else:
        print(f"  No signals extracted")

    # Gating breakdown
    print(f"\n  Gating breakdown:")
    print(f"    Lookthrough gating active:        {canon_result.definition_lock_blocked_count} signals")
    print(f"    Auth threshold blocking:          {canon_result.authorized_threshold_blocked_count} signals")

    # Check for unexpected types
    all_expected = set(EXPECTED_SIGNALS.keys())
    for spec in EXPECTED_SIGNALS.values():
        all_expected.update(spec.get("alt_types", []))
    unexpected = extracted_types - all_expected
    if unexpected:
        print(f"\n  Unexpected signal types extracted: {unexpected}")

    # ── Phase 5: Key Test Assertions ──
    print_section("PHASE 5: Key Test Assertions")

    assertions = []

    # Test 1: Issuer cap should be BREACH (authorized threshold in IPS)
    issuer_signals = canonical_types.get("issuer_cap_breach", []) + \
                     canonical_types.get("concentration_breach", []) + \
                     canonical_types.get("position_limit_breach", [])
    # Filter for Alpina-related signals
    alpina_signals = [s for s in issuer_signals
                      if "alpina" in str(s.title).lower() or "issuer" in str(s.title).lower()]
    if alpina_signals:
        alpina_breaches = [s for s in alpina_signals if s.canonical_status == CanonicalStatus.BREACH]
        if alpina_breaches:
            assertions.append(("PASS", "Issuer cap (Alpina) is BREACH (authorized threshold in IPS)"))
        else:
            assertions.append(("FAIL", "Issuer cap (Alpina) should be BREACH but is OBSERVATION"))
    else:
        # Check if any concentration breach might be Alpina
        any_concentration = canonical_types.get("concentration_breach", [])
        if any_concentration:
            assertions.append(("PARTIAL", f"Concentration breach found but unclear if Alpina: {[s.title for s in any_concentration]}"))
        else:
            assertions.append(("MISS", "Issuer cap (Alpina) signal not extracted"))

    # Test 2: Fee discrepancy should be BREACH (signed schedule present)
    fee_signals = canonical_types.get("fee_discrepancy", [])
    if fee_signals:
        fee_breaches = [s for s in fee_signals if s.canonical_status == CanonicalStatus.BREACH]
        if fee_breaches:
            assertions.append(("PASS", "Fee discrepancy is BREACH (authorized threshold present)"))
        else:
            fee_flags = fee_signals[0].flags if fee_signals else []
            flag_names = [f.value for f in fee_flags]
            if "authorized_threshold_missing" in flag_names:
                assertions.append(("FAIL", "Fee discrepancy is OBSERVATION — authorized_threshold not detected from signed schedule"))
            else:
                assertions.append(("FAIL", f"Fee discrepancy is OBSERVATION — flags: {flag_names}"))
    else:
        assertions.append(("MISS", "Fee discrepancy signal not extracted"))

    # Test 3: Equity max should be OBSERVATION (classification dispute)
    equity_signals = canonical_types.get("mandate_breach", [])
    equity_related = [s for s in equity_signals if "equity" in str(s.title).lower()]
    if equity_related:
        equity_obs = [s for s in equity_related if s.canonical_status == CanonicalStatus.OBSERVATION]
        if equity_obs:
            assertions.append(("PASS", "Equity max is OBSERVATION (classification dispute gates it)"))
        else:
            assertions.append(("FAIL", "Equity max should be OBSERVATION but is BREACH"))
    else:
        assertions.append(("SKIP", "Equity max signal not extracted (may be filtered due to dispute)"))

    # Test 4: Fund concentration should be OBSERVATION (look-through required)
    fund_signals = canonical_types.get("concentration_breach", [])
    fund_related = [s for s in fund_signals if "fund" in str(s.title).lower() or "etf" in str(s.title).lower()]
    if fund_related:
        fund_obs = [s for s in fund_related if s.canonical_status == CanonicalStatus.OBSERVATION]
        if fund_obs:
            assertions.append(("PASS", "Fund concentration is OBSERVATION (look-through required)"))
        else:
            assertions.append(("FAIL", "Fund concentration should be OBSERVATION but is BREACH"))
    else:
        assertions.append(("SKIP", "Fund concentration signal not separately extracted"))

    # Test 5: Missing KID should be OBSERVATION (blocker)
    kid_signals = canonical_types.get("compliance_flag", []) + canonical_types.get("missing_kid", [])
    kid_related = [s for s in kid_signals if "kid" in str(s.title).lower() or "priips" in str(s.title).lower()]
    if kid_related:
        kid_obs = [s for s in kid_related if s.canonical_status == CanonicalStatus.OBSERVATION]
        if kid_obs:
            assertions.append(("PASS", "Missing KID is OBSERVATION (blocker category)"))
        else:
            assertions.append(("FAIL", "Missing KID should be OBSERVATION but is BREACH"))
    else:
        assertions.append(("MISS", "Missing KID signal not extracted"))

    # Test 6: Withdrawal should be OBSERVATION (event)
    wd_signals = canonical_types.get("withdrawal_request", [])
    if wd_signals:
        wd_obs = [s for s in wd_signals if s.canonical_status == CanonicalStatus.OBSERVATION]
        if wd_obs:
            assertions.append(("PASS", "Withdrawal request is OBSERVATION (event category)"))
        else:
            assertions.append(("FAIL", "Withdrawal request should be OBSERVATION but is BREACH"))
    else:
        assertions.append(("MISS", "Withdrawal request signal not extracted"))

    print()
    for status, msg in assertions:
        icon = {"PASS": "✓", "FAIL": "✗", "MISS": "?", "SKIP": "-", "PARTIAL": "~"}.get(status, " ")
        print(f"    [{icon}] {status}: {msg}")

    # Summary
    passed = sum(1 for s, _ in assertions if s == "PASS")
    failed = sum(1 for s, _ in assertions if s == "FAIL")
    missed = sum(1 for s, _ in assertions if s == "MISS")

    print(f"\n  Summary: {passed} passed, {failed} failed, {missed} missed")

    print(f"\n{'=' * 80}")

    return {
        "total_extracted": total_raw,
        "breaches": breaches_after,
        "observations": observations_after,
        "dropped": dropped_after,
        "merged": merged_after,
        "assertions": assertions,
    }


def main():
    """Run the end-to-end wealth test."""

    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set.")
        print("Set it with: export GOOGLE_API_KEY=your-key-here")
        print("\nTo get a key: https://aistudio.google.com/apikey")
        sys.exit(1)

    print_header("E2E TEST: Meridian Wealth — Stonebridge Family Office V2")
    print(f"  Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer")
    print(f"  Pack: wealth")
    print(f"  Document: evals/datasets/wealth_e2e_stonebridge.txt")

    # Load document
    document_text = load_document()
    print(f"  Document length: {len(document_text)} chars")

    # Phase 1: IntakeAgent extraction
    print(f"\n  Running IntakeAgent (Gemini 3 Flash + Thinking Mode)...")
    start = time.time()

    try:
        extraction_result = run_intake_agent(document_text, api_key)
    except Exception as e:
        print(f"\n  ERROR: IntakeAgent failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    extraction_time = time.time() - start
    print(f"  Extraction complete in {extraction_time:.1f}s")
    print(f"  Candidates: {extraction_result.total_candidates}")

    # Phase 2: Canonicalize
    print(f"\n  Running Canonicalizer...")
    clear_registry_cache()

    candidate_dicts = extraction_to_candidate_dicts(extraction_result)

    # Save raw extraction for debugging
    raw_output_path = Path(__file__).parent / "outputs"
    raw_output_path.mkdir(exist_ok=True)

    raw_data = {
        "document_source": "wealth_e2e_stonebridge.txt",
        "pack": "wealth",
        "extraction_time_s": extraction_time,
        "total_candidates": extraction_result.total_candidates,
        "candidates": candidate_dicts,
        "thinking_summary": extraction_result.thinking_summary,
        "extraction_notes": extraction_result.extraction_notes,
    }

    with open(raw_output_path / "wealth_e2e_stonebridge_raw.json", "w") as f:
        json.dump(raw_data, f, indent=2, default=str)
    print(f"  Raw extraction saved to evals/outputs/wealth_e2e_stonebridge_raw.json")

    canon_result = canonicalize(candidate_dicts, "wealth")

    # Phase 3: Analyze
    results = analyze_results(extraction_result, canon_result, candidate_dicts)

    # Save canonical results
    canon_data = {
        "breach_count": canon_result.breach_count,
        "observation_count": canon_result.observation_count,
        "dropped_count": canon_result.dropped_count,
        "merged_count": canon_result.merged_count,
        "event_count": canon_result.event_count,
        "threshold_breach_count": canon_result.threshold_breach_count,
        "threshold_observation_count": canon_result.threshold_observation_count,
        "definition_lock_blocked_count": canon_result.definition_lock_blocked_count,
        "authorized_threshold_blocked_count": canon_result.authorized_threshold_blocked_count,
        "signals": [
            {
                "source_candidate_id": s.source_candidate_id,
                "signal_type": s.signal_type,
                "canonical_status": s.canonical_status.value,
                "severity": s.severity,
                "completeness_score": s.completeness_score,
                "missing_fields": s.missing_fields,
                "flags": [f.value for f in s.flags],
                "title": s.title,
                "dedupe_key": s.dedupe_key,
                "merged_from": s.merged_from,
                "evidence_refs": s.evidence_refs,
            }
            for s in canon_result.signals
        ],
    }

    with open(raw_output_path / "wealth_e2e_stonebridge_canon.json", "w") as f:
        json.dump(canon_data, f, indent=2)
    print(f"  Canonical results saved to evals/outputs/wealth_e2e_stonebridge_canon.json")

    return results


if __name__ == "__main__":
    main()
