#!/usr/bin/env python3
"""
Demo Canonicalization Script — Orion v2 + Stonebridge

Runs both packs through IntakeAgent + Canonicalizer and produces summary
matching demo_video.py expectations:

Expected output:
  - Treasury (Orion v2): 2 breaches (RCF 92%>85%, Covenant CHF 96.4k<100k)
  - Wealth (Stonebridge): 2 breaches (Alpina 8.4%>7%, Fee 0.45% vs 0.30%)
  - Total: 4 breaches, 11 observations

Usage:
    python evals/demo_canonicalization.py              # Run full pipeline
    python evals/demo_canonicalization.py --cached     # Use cached extraction results
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


# =============================================================================
# Configuration
# =============================================================================

PACKS = {
    "treasury": {
        "document": "evals/datasets/treasury_e2e_orion_v2.txt",
        "output_prefix": "treasury_e2e_orion_v2",
        "metadata": {
            "entity": "Orion Metals Trading AG",
            "week": "W10/2026",
            "compiled": "2026-03-03",
        },
        "expected_breaches": 2,
        "expected_breach_types": ["position_limit_breach", "covenant_breach"],
    },
    "wealth": {
        "document": "evals/datasets/wealth_e2e_stonebridge.txt",
        "output_prefix": "wealth_e2e_stonebridge",
        "metadata": {
            "client": "Stonebridge Family Office",
            "firm": "Meridian Private Wealth SA",
            "created": "2026-03-03",
        },
        "expected_breaches": 2,
        "expected_breach_types": ["concentration_breach", "fee_discrepancy"],
    },
}


# =============================================================================
# Pipeline Functions
# =============================================================================

def load_document(pack: str) -> str:
    """Load document for a pack."""
    doc_path = project_root / PACKS[pack]["document"]
    return doc_path.read_text()


def run_intake_agent(document_text: str, pack: str, api_key: str):
    """Run IntakeAgent to extract candidate signals."""
    from coprocessor.agents.intake_agent import IntakeAgent

    agent = IntakeAgent(
        api_key=api_key,
        use_cache=False,
        use_thinking=True,
        thinking_budget=8192,
    )

    result = agent.extract_signals_sync(
        content=document_text,
        pack=pack,
        document_source=PACKS[pack]["document"],
        document_metadata=PACKS[pack]["metadata"],
    )

    return result


def extraction_to_candidate_dicts(result, prefix: str) -> List[Dict[str, Any]]:
    """Convert ExtractionResult candidates to dicts for Canonicalizer."""
    candidates = []
    for i, candidate in enumerate(result.candidates):
        candidates.append({
            "id": f"{prefix}{i}",
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


def load_cached_candidates(pack: str) -> Optional[List[Dict[str, Any]]]:
    """Load cached extraction results if available."""
    cache_path = project_root / "evals" / "outputs" / f"{PACKS[pack]['output_prefix']}_raw.json"
    if cache_path.exists():
        with open(cache_path) as f:
            data = json.load(f)
        return data.get("candidates", [])
    return None


def save_results(pack: str, raw_data: Dict, canon_data: Dict):
    """Save extraction and canonicalization results."""
    output_path = project_root / "evals" / "outputs"
    output_path.mkdir(exist_ok=True)

    prefix = PACKS[pack]["output_prefix"]

    with open(output_path / f"{prefix}_raw.json", "w") as f:
        json.dump(raw_data, f, indent=2, default=str)

    with open(output_path / f"{prefix}_canon.json", "w") as f:
        json.dump(canon_data, f, indent=2)


# =============================================================================
# Display Functions
# =============================================================================

class C:
    """Colors for terminal output."""
    H = '\033[95m'        # magenta — headers
    B = '\033[94m'        # blue — info
    CY = '\033[96m'       # cyan — labels
    G = '\033[92m'        # green — success
    W = '\033[90m'        # dark grey — text
    R = '\033[91m'        # red — breach
    DIM = '\033[2m'       # dim
    BOLD = '\033[1m'
    _ = '\033[0m'         # reset


def print_header(text: str):
    w = 70
    print(f"\n{C.BOLD}{C.H}{'━' * w}{C._}")
    print(f"{C.BOLD}{C.H}  {text}{C._}")
    print(f"{C.BOLD}{C.H}{'━' * w}{C._}\n")


def print_section(text: str):
    print(f"\n  {C.BOLD}{C.CY}── {text} ──{C._}")


def print_signal(sig, index: int):
    """Print a canonical signal with status icon."""
    if sig.canonical_status == CanonicalStatus.BREACH:
        icon = f"{C.R}██ BREACH{C._}"
    elif sig.canonical_status == CanonicalStatus.OBSERVATION:
        icon = f"{C.CY}░░ obs   {C._}"
    elif sig.canonical_status == CanonicalStatus.MERGED:
        icon = f"{C.DIM}>> merged{C._}"
    else:
        icon = f"{C.DIM}XX drop  {C._}"

    title = sig.title[:50] + "..." if len(sig.title) > 50 else sig.title
    print(f"  {icon}  {C.W}{title}{C._}")


# =============================================================================
# Main Pipeline
# =============================================================================

def run_pack(pack: str, api_key: Optional[str], use_cached: bool = False):
    """Run extraction + canonicalization for a single pack."""

    print_section(f"{pack.upper()}: {PACKS[pack]['metadata'].get('entity') or PACKS[pack]['metadata'].get('client')}")

    clear_registry_cache()

    # Try cached first if requested
    if use_cached:
        candidates = load_cached_candidates(pack)
        if candidates:
            print(f"  {C.DIM}Using cached extraction ({len(candidates)} candidates){C._}")
        else:
            print(f"  {C.DIM}No cache found, running extraction...{C._}")
            use_cached = False

    if not use_cached:
        if not api_key:
            print(f"  {C.R}ERROR: GOOGLE_API_KEY required for extraction{C._}")
            return None

        document_text = load_document(pack)
        print(f"  {C.DIM}Document: {len(document_text)} chars{C._}")

        print(f"  {C.B}Running IntakeAgent...{C._}")
        start = time.time()
        extraction_result = run_intake_agent(document_text, pack, api_key)
        elapsed = time.time() - start
        print(f"  {C.DIM}Extraction complete in {elapsed:.1f}s{C._}")

        prefix = "E" if pack == "treasury" else "W"
        candidates = extraction_to_candidate_dicts(extraction_result, prefix)

        # Save raw extraction
        raw_data = {
            "document_source": PACKS[pack]["document"],
            "pack": pack,
            "extraction_time_s": elapsed,
            "total_candidates": len(candidates),
            "candidates": candidates,
            "thinking_summary": extraction_result.thinking_summary,
            "extraction_notes": extraction_result.extraction_notes,
        }
    else:
        raw_data = {"candidates": candidates, "pack": pack}

    # Canonicalize
    print(f"  {C.B}Running Canonicalizer...{C._}")
    canon_result = canonicalize(candidates, pack)

    # Display signals
    print(f"\n  {C.BOLD}Signals:{C._}")
    for i, sig in enumerate(canon_result.signals):
        if sig.canonical_status != CanonicalStatus.MERGED:
            print_signal(sig, i)

    # Save results
    canon_data = {
        "breach_count": canon_result.breach_count,
        "observation_count": canon_result.observation_count,
        "dropped_count": canon_result.dropped_count,
        "merged_count": canon_result.merged_count,
        "signals": [
            {
                "source_candidate_id": s.source_candidate_id,
                "signal_type": s.signal_type,
                "canonical_status": s.canonical_status.value,
                "severity": s.severity,
                "title": s.title,
                "flags": [f.value for f in s.flags],
            }
            for s in canon_result.signals
        ],
    }
    save_results(pack, raw_data, canon_data)

    return canon_result


def main():
    """Run the demo canonicalization pipeline."""

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cached', action='store_true', help='Use cached extraction results')
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key and not args.cached:
        print(f"{C.R}ERROR: GOOGLE_API_KEY not set.{C._}")
        print("Set it with: export GOOGLE_API_KEY=your-key-here")
        print("Or use --cached to use previously saved extraction results.")
        sys.exit(1)

    print_header("DEMO: Canonicalization Pipeline")
    print(f"  {C.W}Pipeline: Document → IntakeAgent (Gemini 3) → Canonicalizer{C._}")
    print(f"  {C.W}Packs: Treasury (Orion v2) + Wealth (Stonebridge){C._}")
    print(f"  {C.W}Expected: 4 breaches (2 + 2), 11 observations{C._}")

    results = {}

    # Run both packs
    for pack in ["treasury", "wealth"]:
        result = run_pack(pack, api_key, use_cached=args.cached)
        if result:
            results[pack] = result

    # Summary
    print_header("SUMMARY")

    total_breaches = 0
    total_observations = 0
    all_passed = True

    for pack, result in results.items():
        expected = PACKS[pack]["expected_breaches"]
        actual = result.breach_count
        status = "PASS" if actual == expected else "FAIL"
        color = C.G if status == "PASS" else C.R

        if actual != expected:
            all_passed = False

        total_breaches += actual
        total_observations += result.observation_count

        pack_name = PACKS[pack]["metadata"].get("entity") or PACKS[pack]["metadata"].get("client")
        print(f"  {color}{status}{C._}  {pack.upper():10s}  breaches: {actual}/{expected}  observations: {result.observation_count}")

        # Show breach types
        breach_signals = [s for s in result.signals if s.canonical_status == CanonicalStatus.BREACH]
        for sig in breach_signals:
            print(f"       {C.R}→ {sig.signal_type}: {sig.title[:40]}...{C._}")

    print()
    print(f"  {C.BOLD}{'─' * 50}{C._}")
    print(f"  {C.BOLD}Total breaches:      {total_breaches}/4{C._}")
    print(f"  {C.BOLD}Total observations:  {total_observations}{C._}")
    print(f"  {C.BOLD}{'─' * 50}{C._}")

    if all_passed and total_breaches == 4:
        print(f"\n  {C.G}{C.BOLD}ALL CHECKS PASSED — matches demo_video.py expectations{C._}")
    else:
        print(f"\n  {C.R}{C.BOLD}MISMATCH — expected 4 breaches (2+2){C._}")

    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
