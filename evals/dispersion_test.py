#!/usr/bin/env python3
"""
Extraction Stability Test (Dispersion Analysis)

Runs the same documents through the extraction pipeline multiple times
to measure signal stability and variance.

Usage:
    GOOGLE_API_KEY=... python evals/dispersion_test.py

Results are printed to stdout. See EXTRACTION_STABILITY_REPORT.md for
analysis of a 10-run test.
"""

import os
import sys
from collections import Counter

sys.path.insert(0, '.')

# Check for API key
if not os.environ.get("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY not set")
    sys.exit(1)

from coprocessor.agents.intake_agent import IntakeAgent

# Test documents (inline for reproducibility)
TREASURY_DOC = """ORION METALS TRADING AG — TREASURY WEEKLY PACK (Messy Input, Synthetic Demo)
Week: W10 / 2026 | Compiled: 2026-03-03 06:42 CET
Entity: Orion Metals Trading AG (synthetic) | HQ: Zurich (CH)

Key items:
A) Confirmed threshold breach: RCF utilization above internal limit (85%) as of 2026-03-02 EOD.
B) Confirmed covenant breach: Minimum Unrestricted Cash covenant (>= CHF 100,000) breached at EOD 2026-03-02 under agreed definition.
C) Potential FX "limit breach" is NOT confirmed (threshold not sourced / definition unclear) — treat as observation.
D) Operational events: one supplier payment blocked; fee spike flagged; pending settlement affects tomorrow morning cash.

Internal computed unrestricted cash @ EOD 2026-03-02: CHF 96,400 (min required 100,000)
Definition note (IMPORTANT): excludes overdraft limits, bank holds, LC margin, and pending settlement.

RCF utilization soft limit: 85% (escalate if exceeded)
Facility limit: CHF 2,000,000
Drawn amount at EOD 2026-03-02: CHF 1,840,000
=> Utilization = 1,840,000 / 2,000,000 = 92.0% (breaches internal 85% limit)

From: AlpineBank Covenant Officer
Confirmed: for covenant testing, "Unrestricted Cash" excludes:
(i) overdraft/credit facility limits,
(ii) blocked/held balances,
(iii) LC margin and pledged cash,
(iv) pending settlement proceeds until booked (value date).
Covenant threshold remains CHF 100,000 at all times.

Payment CHF 58,700 blocked by bank due beneficiary mismatch ("Baltic Steel OU" vs "Baltic Steel OÜ").
Fees posted 03.02: CHF 4,980 (see details)
FX: hedge target band 40-70% for forecast EUR payables, NOT a hard limit
"""

WEALTH_DOC = """MERIDIAN PRIVATE WEALTH SA — WEALTH MANAGEMENT PACK (Messy Input, Synthetic Demo)
Client: Stonebridge Family Office (synthetic) | Mandate: Discretionary (Balanced)
Created: 2026-03-03 12:10 CET

Constraints (relevant excerpts):
Single issuer cap (direct securities): max 7.0% of total portfolio value (TPV)
Single fund cap: max 12.0% of TPV (internal control; requires look-through flag in registry)
Equity exposure: hard max 40% (but classification must be consistent)
Liquidity buffer: min 15% cash + T-bills (value date alignment required)
PRIIPs/KID required for structured products
Suitability refresh target: 12 months

TOTAL ASSETS: CHF 6,102,880.40

Cash & T-bills: CHF 820,000 (13.6%) <-- below 15% (but pending settlement exists)
Equities: CHF 2,540,000 (42.1%) <-- above 40% (but classification dispute exists)

1. Alpina Energy AG (equity): CHF 507,000 (8.4%) <-- issuer cap breach (7%)
2. Global Equity UCITS ETF: CHF 770,000 (12.7%) <-- fund cap issue (requires look-through)
3. EM Active Fund: CHF 540,000 (8.9%) <-- single-country cap needs lookthrough (not provided)
4. Structured Note "ZEN Autocall 2025": CHF 240,000 (4.0%) <-- KID missing (blocker)

Pending settlement proceeds expected: CHF 220,000
Client requested withdrawal CHF 500,000 by 2026-03-12 (email)

Signed Fee Schedule: Custody fee: 0.30% p.a. on total assets
Custodian invoice: 0.45% p.a. equivalent for Q1 (mismatch!)

Suitability questionnaire date in CRM is 2024-09-15 (stale > 12 months).
"""

NUM_RUNS = 10


def run_extraction(agent, content, pack, doc_name):
    """Run extraction and return signal summary."""
    try:
        result = agent.extract_signals_sync(
            content=content,
            pack=pack,
            document_source=doc_name
        )

        signals = []
        for sig in result.candidates:
            signals.append({
                "type": sig.signal_type,
            })

        return {
            "total": len(result.candidates),
            "signals": signals,
            "error": None
        }
    except Exception as e:
        return {
            "total": -1,
            "signals": [],
            "error": str(e)[:50]
        }


def main():
    agent = IntakeAgent(use_thinking=False)

    results = {
        "treasury": [],
        "wealth": []
    }

    print("=" * 60)
    print("DISPERSION TEST: 10 runs per pack")
    print("=" * 60)
    print()

    # Run Treasury pack
    print("TREASURY (Orion) - 10 runs:")
    print("-" * 40)
    for i in range(NUM_RUNS):
        r = run_extraction(agent, TREASURY_DOC, "treasury", "orion_pack")
        results["treasury"].append(r)
        if r["error"]:
            print(f"  Run {i+1:2d}: ERROR - {r['error']}")
        else:
            print(f"  Run {i+1:2d}: {r['total']:2d} signals")

    print()

    # Run Wealth pack
    print("WEALTH (Meridian) - 10 runs:")
    print("-" * 40)
    for i in range(NUM_RUNS):
        r = run_extraction(agent, WEALTH_DOC, "wealth", "meridian_pack")
        results["wealth"].append(r)
        if r["error"]:
            print(f"  Run {i+1:2d}: ERROR - {r['error']}")
        else:
            print(f"  Run {i+1:2d}: {r['total']:2d} signals")

    print()
    print("=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

    for pack_name, runs in results.items():
        valid_runs = [r for r in runs if r["error"] is None]
        error_count = len(runs) - len(valid_runs)

        if not valid_runs:
            print(f"\n{pack_name.upper()}: All runs failed!")
            continue

        totals = [r["total"] for r in valid_runs]
        avg_total = sum(totals) / len(totals)

        print(f"\n{pack_name.upper()} ({len(valid_runs)}/10 successful):")
        print(f"  Signals: min={min(totals)}, max={max(totals)}, avg={avg_total:.1f}")
        if error_count > 0:
            print(f"  Errors:  {error_count} runs failed")

        if len(set(totals)) == 1:
            print(f"  ✓ DETERMINISTIC: All runs = {totals[0]} signals")
        else:
            print(f"  ⚠ VARIANCE: {sorted(set(totals))}")

    print()
    print("=" * 60)
    print("SIGNAL TYPES PER PACK")
    print("=" * 60)

    for pack_name, runs in results.items():
        valid_runs = [r for r in runs if r["error"] is None]
        if not valid_runs:
            continue

        print(f"\n{pack_name.upper()}:")
        type_counts = Counter()
        for r in valid_runs:
            for sig in r["signals"]:
                type_counts[sig["type"]] += 1

        for sig_type, count in type_counts.most_common():
            avg = count / len(valid_runs)
            print(f"  {sig_type:30s}: {avg:.1f}/run")


if __name__ == "__main__":
    main()
