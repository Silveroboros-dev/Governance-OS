"""
End-to-End Test: Stonebridge Family Office — Wealth Pack

Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer → Results

Expected signals from the document:
1. concentration_breach: Alpina Energy AG 8.4% > 7% issuer cap
   - SHOULD be BREACH — authorized threshold in IPS, lookthrough available for direct holding
2. fee_discrepancy: 0.45% charged vs 0.30% expected
   - SHOULD be BREACH — signed fee schedule provides authorized threshold
3. concentration_breach (fund): Global Equity UCITS ETF 12.7% > 12% cap
   - SHOULD be OBSERVATION — requires lookthrough (fund), not available
4. mandate_breach: Equity 42.1% > 40% max
   - SHOULD be OBSERVATION — requires lookthrough, classification dispute
5. withdrawal_request: CHF 500k by March 12
   - SHOULD be OBSERVATION — event category
6. settlement_pending_cash: CHF 220k pending
   - SHOULD be OBSERVATION — event category
7. lookthrough_missing: EM Active Fund
   - SHOULD be OBSERVATION — event category
8. compliance_flag: Missing KID (ZEN Autocall), stale suitability
   - SHOULD be OBSERVATION — event category

Key challenges:
- Mixed valuation dates (Feb 28 vs Mar 02)
- Classification mismatch (Eiger certificate = equity in PMS, structured at custodian)
- Lookthrough available for direct holdings, missing for funds
- Authorized threshold present for issuer cap and fee schedule
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
    """Load the Stonebridge wealth management pack document."""
    doc_path = Path(__file__).parent / "datasets" / "wealth_e2e_stonebridge.txt"
    return doc_path.read_text()


def run_intake_agent(document_text: str, api_key: Optional[str] = None):
    """Run IntakeAgent to extract candidate signals from document."""
    from coprocessor.agents.intake_agent import IntakeAgent

    agent = IntakeAgent(
        api_key=api_key,
        use_cache=False,
        use_thinking=True,
        thinking_budget=8192,
    )

    result = agent.extract_signals_sync(
        content=document_text,
        pack="wealth",
        document_source="evals/datasets/wealth_e2e_stonebridge.txt",
        document_metadata={
            "client": "Stonebridge Family Office",
            "firm": "Meridian Private Wealth SA",
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
    "concentration_breach": {
        "description": "Alpina Energy AG 8.4% > 7% issuer cap (BREACH); Fund 12.7% > 12% (observation)",
        "should_extract": True,
        "expected_canon_status": "breach",  # At least one should be BREACH (Alpina direct holding)
        "reason": "Alpina is direct holding with authorized threshold in IPS; fund requires lookthrough",
    },
    "fee_discrepancy": {
        "description": "0.45% p.a. invoiced vs 0.30% signed fee schedule",
        "should_extract": True,
        "expected_canon_status": "breach",  # signed fee schedule = authorized threshold
        "reason": "Signed fee schedule provides authorized threshold evidence",
    },
    "mandate_breach": {
        "description": "Equity 42.1% > 40% max",
        "should_extract": True,
        "expected_canon_status": "observation",
        "reason": "mandate_breach requires lookthrough; classification dispute means equity % uncertain",
    },
    "withdrawal_request": {
        "description": "CHF 500k withdrawal by March 12",
        "should_extract": True,
        "expected_canon_status": "observation",  # event category
        "reason": "Event-category signal; ~8.3% of portfolio",
    },
    "settlement_pending_cash": {
        "description": "CHF 220k pending settlement",
        "should_extract": True,
        "expected_canon_status": "observation",  # event category
        "reason": "Event-category signal; affects liquidity calculation",
    },
    "lookthrough_missing": {
        "description": "EM Active Fund — country breakdown not available",
        "should_extract": True,
        "expected_canon_status": "observation",  # event category
        "reason": "Event-category signal; single-country cap cannot be verified",
    },
    "compliance_flag": {
        "description": "Missing KID (ZEN Autocall), stale suitability (>12 months)",
        "should_extract": True,
        "expected_canon_status": "observation",  # event category
        "reason": "Event-category; product governance blocker",
    },
}


def print_header(title: str):
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


def print_section(title: str):
    print(f"\n  --- {title} ---")


def analyze_results(extraction_result, canon_result, candidate_dicts):
    """Analyze and report on e2e results."""

    print_header("E2E RESULTS: Stonebridge Family Office")

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
        for key in ["constraint", "subject", "client", "charged", "expected",
                     "current", "limit", "metric", "threshold", "current_value",
                     "amount", "percent_of_portfolio", "rule", "missing_data",
                     "impact", "issue_type", "regulation", "current_risk",
                     "target_risk", "anomaly_type"]:
            if key in c.payload and c.payload[key]:
                print(f"         {key}: {c.payload[key]}")

        if c.source_spans:
            span_text = c.source_spans[0].text[:80]
            print(f"         evidence: \"{span_text}{'...' if len(c.source_spans[0].text) > 80 else ''}\"")

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
            "breach": "!!", "observation": "??", "dropped": "XX", "merged": ">>",
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
        extracted = expected_type in extracted_types
        canon_signals = canonical_types.get(expected_type, [])

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

    if total_raw > 0:
        print(f"  Raw LLM signals:           {total_raw}")
        print(f"  → Breaches (threshold):    {breaches_after}")
        print(f"  → Observations:            {observations_after}")
        print(f"    - Events (always obs):   {canon_result.event_count}")
        print(f"    - Downgraded thresholds: {canon_result.threshold_observation_count}")
        print(f"  → Dropped (invalid type):  {dropped_after}")
        print(f"  → Merged (deduped):        {merged_after}")
        print(f"  False breach prevention:   {false_breach_prevented}/{total_raw} "
              f"({false_breach_prevented/total_raw*100:.0f}%)")
        if canon_result.definition_lock_blocked_count > 0:
            print(f"  Definition lock blocks:    {canon_result.definition_lock_blocked_count}")
        if canon_result.authorized_threshold_blocked_count > 0:
            print(f"  Auth threshold blocks:     {canon_result.authorized_threshold_blocked_count}")
    else:
        print(f"  No signals extracted.")

    # Lookthrough gating check
    lookthrough_blocked = [s for s in canon_result.signals
                          if CanonicalFlag.LOOKTHROUGH_MISSING in s.flags
                          or CanonicalFlag.LOOKTHROUGH_REQUIRED in s.flags]
    if lookthrough_blocked:
        print(f"\n  Lookthrough gating active: {len(lookthrough_blocked)} signals affected")
        for s in lookthrough_blocked:
            print(f"    {s.source_candidate_id}: {s.signal_type} → {s.canonical_status.value}")

    # Unexpected types
    unexpected = extracted_types - set(EXPECTED_SIGNALS.keys())
    if unexpected:
        print(f"\n  Unexpected signal types extracted: {unexpected}")

    # ── Phase 5: Gap Analysis ──
    print_section("PHASE 5: Gap Analysis")

    gaps = []

    # Check Alpina concentration_breach is BREACH (direct holding with authorized threshold)
    alpina_breach = [s for s in canon_result.signals
                     if s.signal_type == "concentration_breach"
                     and s.canonical_status == CanonicalStatus.BREACH
                     and "alpina" in s.title.lower()]
    if not alpina_breach:
        gaps.append("Alpina concentration_breach not a BREACH — should be BREACH (direct holding, authorized threshold)")

    # Check fee_discrepancy is BREACH (signed fee schedule = authorized threshold)
    fee_signals = [s for s in canon_result.signals
                   if s.signal_type == "fee_discrepancy"
                   and s.canonical_status == CanonicalStatus.BREACH]
    if not fee_signals:
        fee_any = [s for s in canon_result.signals if s.signal_type == "fee_discrepancy"]
        if fee_any:
            gaps.append(f"fee_discrepancy is {fee_any[0].canonical_status.value}, expected BREACH (signed fee schedule)")
        else:
            gaps.append("fee_discrepancy not extracted — LLM missed 0.45% vs 0.30%")

    # Check mandate_breach stays as observation (requires lookthrough)
    mandate_breach = [s for s in canon_result.signals
                      if s.signal_type == "mandate_breach"
                      and s.canonical_status == CanonicalStatus.BREACH]
    if mandate_breach:
        gaps.append("mandate_breach passed as BREACH despite lookthrough requirement")

    # Check fund concentration stays as observation
    fund_breach = [s for s in canon_result.signals
                   if s.signal_type == "concentration_breach"
                   and s.canonical_status == CanonicalStatus.BREACH
                   and "fund" in s.title.lower() or "etf" in s.title.lower()]
    if fund_breach:
        gaps.append("Fund concentration_breach passed as BREACH despite lookthrough requirement")

    if gaps:
        for i, gap in enumerate(gaps, 1):
            print(f"  {i}. {gap}")
    else:
        print(f"  No significant gaps detected.")

    print(f"\n{'=' * 80}")

    return {
        "total_extracted": total_raw,
        "breaches": breaches_after,
        "observations": observations_after,
        "dropped": dropped_after,
        "merged": merged_after,
        "gaps": gaps,
    }


def main():
    """Run the end-to-end wealth test."""

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set.")
        print("Set it with: export GOOGLE_API_KEY=your-key-here")
        sys.exit(1)

    print_header("E2E TEST: Stonebridge Family Office Pack")
    print(f"  Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer")
    print(f"  Pack: wealth")
    print(f"  Document: evals/datasets/wealth_e2e_stonebridge.txt")

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

    # Save raw extraction
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
