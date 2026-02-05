"""
End-to-End Test: Meridian Private Wealth — Ravenwood Trust Pack

Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer → Results

Expected signals from the document (section 6):
1. Liquidity buffer breach/at-risk: 12.6% vs 15% min (PMS) — but custodian shows 15.3%
2. Equity exposure breach: 40.2% vs 40% max (PMS) — classification dispute
3. Fund concentration breach: Global Equity UCITS ETF 13.5% vs 12% cap
4. Lookthrough missing: EM fund exposure vs single-country cap
5. Missing required doc: PRIIPs/KID for ZEN Autocall (product governance blocker)
6. Fee discrepancy: 0.40% charged vs 0.30% expected
7. Suitability stale (process risk — 15 months vs 12-month target)
8. Client request: crypto exposure (mandate conflict)
9. Withdrawal request: CHF 400k (liquidity planning)

Key challenges:
- Mixed valuation dates (Feb 20 vs Feb 24)
- Classification mismatch (certificate = equity in PMS, structured at custodian)
- Pending settlement in custodian cash but not PMS
- Rich wealth vocabulary (12 signal types available)
- Lookthrough gating on concentration_breach and mandate_breach
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
    """Load the Meridian wealth management pack document."""
    doc_path = Path(__file__).parent / "datasets" / "wealth_e2e_meridian.txt"
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
        document_source="evals/datasets/wealth_e2e_meridian.txt",
        document_metadata={
            "client": "Ravenwood Trust",
            "firm": "Meridian Private Wealth SA",
            "created": "2026-02-25",
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
    "mandate_breach": {
        "description": "Equity 40.2% > 40% max, Liquidity 12.6% < 15% min",
        "should_extract": True,
        "expected_canon_status": "observation",
        "reason": "mandate_breach requires lookthrough; classification dispute (Helvetia) means equity % uncertain; "
                  "value date mismatch (Feb 20 vs 24) means liquidity % uncertain",
    },
    "concentration_breach": {
        "description": "Global Equity UCITS ETF 13.5% > 12% single fund cap",
        "should_extract": True,
        "expected_canon_status": "observation",
        "reason": "concentration_breach requires lookthrough per wealth constraint registry",
    },
    "lookthrough_missing": {
        "description": "EM Equity Fund — single-country cap cannot be verified without country breakdown",
        "should_extract": True,
        "expected_canon_status": "any",
        "reason": "lookthrough_missing is an event-category signal, not breach",
    },
    "fee_discrepancy": {
        "description": "0.40% p.a. invoiced vs 0.30% term sheet",
        "should_extract": True,
        "expected_canon_status": "observation",
        "reason": "Threshold + authorized_threshold gate: needs evidence_type=term_sheet to confirm threshold. "
                  "Without authorized source, fee dispute stays observation until verified.",
    },
    "settlement_pending_cash": {
        "description": "CHF 190k pending settlement in custodian cash",
        "should_extract": True,
        "expected_canon_status": "any",
        "reason": "Event-category signal; pending settlement affects liquidity calculation",
    },
    "withdrawal_request": {
        "description": "CHF 400k withdrawal by March 7",
        "should_extract": True,
        "expected_canon_status": "any",
        "reason": "Event-category; withdrawal_request in vocabulary. ~7.6% of portfolio",
    },
    "compliance_flag": {
        "description": "Missing KID for ZEN Autocall, stale suitability, crypto mandate conflict",
        "should_extract": "maybe",
        "expected_canon_status": "any",
        "reason": "Multiple compliance issues could map here; also suitability_drift for stale assessment",
    },
    "suitability_drift": {
        "description": "Suitability 15 months old vs 12-month target; equity overweight",
        "should_extract": "maybe",
        "expected_canon_status": "any",
        "reason": "Could capture both stale assessment and equity drift",
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

    print_header("E2E RESULTS: Meridian Wealth — Ravenwood Trust")

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

    # Check lookthrough gating effectiveness
    mandate_signals = [s for s in canon_result.signals
                      if s.signal_type == "mandate_breach"
                      and s.canonical_status == CanonicalStatus.BREACH]
    if mandate_signals:
        gaps.append("mandate_breach passed as BREACH despite lookthrough requirement — "
                    "payload may include lookthrough_available=True incorrectly")

    concentration_breach_signals = [s for s in canon_result.signals
                                    if s.signal_type == "concentration_breach"
                                    and s.canonical_status == CanonicalStatus.BREACH]
    if concentration_breach_signals:
        gaps.append("concentration_breach passed as BREACH despite lookthrough requirement")

    # Check fee_discrepancy extraction
    if "fee_discrepancy" not in extracted_types:
        gaps.append("Fee discrepancy (0.40% vs 0.30%) not extracted — LLM missed it")

    # Check withdrawal_request extraction
    if "withdrawal_request" not in extracted_types:
        gaps.append("Withdrawal request (CHF 400k) not extracted — LLM missed it")

    # Check suitability
    has_suitability = "suitability_drift" in extracted_types or "compliance_flag" in extracted_types
    if not has_suitability:
        gaps.append("Stale suitability (15m vs 12m target) not captured in any signal type")

    # Check KID missing
    kid_captured = any("kid" in str(c.payload).lower() or "priips" in str(c.payload).lower()
                      for c in extraction_result.candidates)
    if not kid_captured:
        gaps.append("Missing KID/PRIIPs for ZEN Autocall not captured")

    # Cross-type dedup for equity breach
    equity_related = [c for c in extraction_result.candidates
                     if "equity" in str(c.payload).lower() or "40" in str(c.payload).lower()]
    if len(equity_related) > 1:
        gaps.append(f"Multiple signals about equity exposure ({len(equity_related)}) — "
                    f"cross-type dedup opportunity")

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

    print_header("E2E TEST: Meridian Wealth — Ravenwood Trust Pack")
    print(f"  Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer")
    print(f"  Pack: wealth")
    print(f"  Document: evals/datasets/wealth_e2e_meridian.txt")

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
        "document_source": "wealth_e2e_meridian.txt",
        "pack": "wealth",
        "extraction_time_s": extraction_time,
        "total_candidates": extraction_result.total_candidates,
        "candidates": candidate_dicts,
        "thinking_summary": extraction_result.thinking_summary,
        "extraction_notes": extraction_result.extraction_notes,
    }

    with open(raw_output_path / "wealth_e2e_meridian_raw.json", "w") as f:
        json.dump(raw_data, f, indent=2, default=str)
    print(f"  Raw extraction saved to evals/outputs/wealth_e2e_meridian_raw.json")

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

    with open(raw_output_path / "wealth_e2e_meridian_canon.json", "w") as f:
        json.dump(canon_data, f, indent=2)
    print(f"  Canonical results saved to evals/outputs/wealth_e2e_meridian_canon.json")

    return results


if __name__ == "__main__":
    main()
