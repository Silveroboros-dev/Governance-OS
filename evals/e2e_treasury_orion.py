"""
End-to-End Test: Orion Metals Treasury Weekly Pack (v2)

Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer → Results

Expected signals from the document:
1. position_limit_breach: RCF utilization 92% > 85% internal limit
   - SHOULD be BREACH — authorized threshold present in policy
2. covenant_breach: unrestricted cash CHF 96.4k vs CHF 100k min
   - SHOULD be BREACH — definition lock confirmed by bank email
3. fx_exposure_breach: EUR payables ~520k, only 140k hedged
   - SHOULD be OBSERVATION — no hard limit, just target band
4. settlement_failure: CHF 58.7k blocked, beneficiary mismatch
   - SHOULD be OBSERVATION — event category
5. bank_account_anomaly: fee spike CHF 4,980
   - SHOULD be OBSERVATION — event category

Key challenges for the pipeline:
- Conflicting balances: "available" vs "book" vs "unrestricted"
- Definition lock present for covenant (should enable BREACH)
- Authorized threshold present for RCF (should enable BREACH)
- FX has target band, not hard limit (should stay OBSERVATION)
- Events: settlement, fee anomaly (must remain OBSERVATION)
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
    """Load the Orion treasury weekly pack document (v2)."""
    doc_path = Path(__file__).parent / "datasets" / "treasury_e2e_orion_v2.txt"
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
        pack="treasury",
        document_source="evals/datasets/treasury_e2e_orion_v2.txt",
        document_metadata={
            "entity": "Orion Metals Trading AG",
            "week": "W10/2026",
            "compiled": "2026-03-03",
            "type": "treasury_weekly_pack",
        },
    )

    return result


def extraction_to_candidate_dicts(result) -> List[Dict[str, Any]]:
    """Convert ExtractionResult candidates to dicts for Canonicalizer."""
    candidates = []
    for i, candidate in enumerate(result.candidates):
        candidates.append({
            "id": f"E{i}",
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
    "position_limit_breach": {
        "description": "RCF utilization 92% > 85% internal limit",
        "should_extract": True,
        "expected_canon_status": "breach",  # authorized threshold present
        "reason": "RCF limit 85% is documented in Internal Treasury Policy v3.2",
    },
    "covenant_breach": {
        "description": "Unrestricted cash CHF 96.4k vs CHF 100k minimum covenant",
        "should_extract": True,
        "expected_canon_status": "breach",  # definition lock confirmed by bank
        "reason": "Definition locked by AlpineBank Covenant Officer email 2026-03-02",
    },
    "fx_exposure_breach": {
        "description": "EUR payables ~520k, only 140k hedged, 380k unhedged",
        "should_extract": True,
        "expected_canon_status": "observation",  # target band, not hard limit
        "reason": "Policy says 'hedge target band 40-70%', NOT a hard limit",
    },
    "settlement_failure": {
        "description": "Payment CHF 58.7k to Baltic Steel OÜ blocked — beneficiary mismatch",
        "should_extract": True,
        "expected_canon_status": "observation",  # event category
        "reason": "Event-category signal — blocked payment, not a threshold breach",
    },
    "bank_account_anomaly": {
        "description": "Fee spike CHF 4,980 posted",
        "should_extract": True,
        "expected_canon_status": "observation",  # event category
        "reason": "Event-category signal — fee anomaly requiring investigation",
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

    print_header("E2E RESULTS: Orion Metals Treasury Weekly Pack (v2)")

    # ── Phase 1: IntakeAgent Extraction ──
    print_section("PHASE 1: IntakeAgent Extraction (Gemini 3)")
    print(f"  Total candidates extracted: {extraction_result.total_candidates}")
    print(f"  High confidence (≥0.9):     {extraction_result.high_confidence_count}")
    print(f"  Needs verification (<0.7):  {extraction_result.requires_verification_count}")

    if extraction_result.extraction_notes:
        print(f"\n  Extraction notes:")
        for line in extraction_result.extraction_notes.split("\n"):
            if line.strip():
                print(f"    {line.strip()}")

    if extraction_result.thinking_summary:
        print(f"\n  Thinking summary (first 500 chars):")
        summary = extraction_result.thinking_summary[:500]
        for line in summary.split("\n"):
            print(f"    {line}")
        if len(extraction_result.thinking_summary) > 500:
            print(f"    ... ({len(extraction_result.thinking_summary)} total chars)")

    # List all extracted candidates
    print(f"\n  Extracted candidates:")
    type_counts = {}
    for i, c in enumerate(extraction_result.candidates):
        conf_icon = "●" if c.confidence >= 0.9 else "◐" if c.confidence >= 0.7 else "○"
        print(f"    [{conf_icon}] E{i}: {c.signal_type} (conf={c.confidence:.2f})")
        # Show key payload fields
        for key in ["covenant_name", "entity", "asset", "currency_pair", "account",
                     "counterparty", "actual_ratio", "required_ratio", "current_ratio",
                     "threshold", "current_exposure", "limit", "amount", "anomaly_type",
                     "failure_reason"]:
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
    print_section("PHASE 4: Value Assessment (Category-Aware)")

    total_raw = len(extraction_result.candidates)
    breaches_after = canon_result.breach_count
    observations_after = canon_result.observation_count
    dropped_after = canon_result.dropped_count
    merged_after = canon_result.merged_count

    false_breach_prevented = total_raw - breaches_after

    print(f"  Raw LLM signals:           {total_raw}")
    print(f"  → Breaches (confirmed):    {breaches_after}")
    print(f"  → Observations (at-risk):  {observations_after}")
    print(f"  → Dropped (invalid type):  {dropped_after}")
    print(f"  → Merged (deduped):        {merged_after}")
    print(f"  False breach prevention:   {false_breach_prevented}/{total_raw} "
          f"({false_breach_prevented/total_raw*100:.0f}%)" if total_raw > 0 else "  No signals extracted")

    # Category-aware breakdown
    print(f"\n  Category breakdown:")
    print(f"    Event-category signals (always observation): {canon_result.event_count}")
    print(f"    Threshold signals → breach:                  {canon_result.threshold_breach_count}")
    print(f"    Threshold signals → observation (gated):     {canon_result.threshold_observation_count}")
    print(f"    Definition-lock blocked:                     {canon_result.definition_lock_blocked_count}")
    print(f"    Authorized-threshold blocked:                {canon_result.authorized_threshold_blocked_count}")

    # Check for unexpected types (not in our expected list)
    unexpected = extracted_types - set(EXPECTED_SIGNALS.keys())
    if unexpected:
        print(f"\n  Unexpected signal types extracted: {unexpected}")

    # ── Phase 5: Gap Analysis ──
    print_section("PHASE 5: Gap Analysis")

    gaps = []

    # Check RCF position_limit_breach extraction and status
    rcf_signals = [s for s in canon_result.signals
                   if s.signal_type == "position_limit_breach"
                   and s.canonical_status != CanonicalStatus.MERGED]
    if not rcf_signals:
        gaps.append("RCF position_limit_breach not extracted — should be BREACH with 92% > 85%")
    elif rcf_signals[0].canonical_status != CanonicalStatus.BREACH:
        gaps.append(f"RCF position_limit_breach is {rcf_signals[0].canonical_status.value}, expected BREACH")

    # Check covenant_breach extraction and status (should be BREACH with definition lock)
    covenant_signals = [s for s in canon_result.signals
                       if s.signal_type == "covenant_breach"
                       and s.canonical_status != CanonicalStatus.MERGED]
    if not covenant_signals:
        gaps.append("covenant_breach not extracted — should be BREACH with definition lock")
    elif covenant_signals[0].canonical_status != CanonicalStatus.BREACH:
        gaps.append(f"covenant_breach is {covenant_signals[0].canonical_status.value}, expected BREACH (definition lock present)")

    # Check FX stays as observation (target band, not hard limit)
    fx_signals = [s for s in canon_result.signals
                  if s.signal_type == "fx_exposure_breach"
                  and s.canonical_status != CanonicalStatus.MERGED]
    if fx_signals and fx_signals[0].canonical_status == CanonicalStatus.BREACH:
        gaps.append("fx_exposure_breach is BREACH but should be OBSERVATION (target band, not hard limit)")

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
    """Run the end-to-end treasury test."""

    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set.")
        print("Set it with: export GOOGLE_API_KEY=your-key-here")
        print("\nTo get a key: https://aistudio.google.com/apikey")
        sys.exit(1)

    print_header("E2E TEST: Orion Metals Treasury Weekly Pack (v2)")
    print(f"  Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer")
    print(f"  Pack: treasury")
    print(f"  Document: evals/datasets/treasury_e2e_orion_v2.txt")

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
        "document_source": "treasury_e2e_orion_v2.txt",
        "pack": "treasury",
        "extraction_time_s": extraction_time,
        "total_candidates": extraction_result.total_candidates,
        "candidates": candidate_dicts,
        "thinking_summary": extraction_result.thinking_summary,
        "extraction_notes": extraction_result.extraction_notes,
    }

    with open(raw_output_path / "treasury_e2e_orion_v2_raw.json", "w") as f:
        json.dump(raw_data, f, indent=2, default=str)
    print(f"  Raw extraction saved to evals/outputs/treasury_e2e_orion_v2_raw.json")

    canon_result = canonicalize(candidate_dicts, "treasury")

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

    with open(raw_output_path / "treasury_e2e_orion_v2_canon.json", "w") as f:
        json.dump(canon_data, f, indent=2)
    print(f"  Canonical results saved to evals/outputs/treasury_e2e_orion_v2_canon.json")

    return results


if __name__ == "__main__":
    main()
