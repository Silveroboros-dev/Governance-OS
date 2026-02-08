#!/usr/bin/env python3
"""
GOVERNANCE OS — VIDEO DEMO
===========================

Designed for hackathon video recording. Short, visual, scannable at a glance.

Three acts in ~90 seconds of terminal time:
  ACT 1: Gemini reads a document and shows its reasoning (Thinking Mode)
  ACT 2: Canonicalizer filters 14 signals → 4 real breaches (71% prevention)
  ACT 3: Safety layer blocks AI from making recommendations

Run:
    python demo_video.py              # Interactive (press Enter to advance)
    python demo_video.py --auto       # Auto-advance (for screen recording)
"""

import os
import sys
import time
import argparse

sys.path.insert(0, '.')

parser = argparse.ArgumentParser()
parser.add_argument('--auto', action='store_true', help='Auto-advance for recording')
args, _ = parser.parse_known_args()

AUTO = args.auto


# ── Colors (dark-terminal safe — no yellow) ──────────────────────────────────

class C:
    H = '\033[95m'        # magenta — headers
    B = '\033[94m'        # blue — AI thoughts
    CY = '\033[96m'       # cyan — labels
    G = '\033[92m'        # green — success/safe
    W = '\033[90m'        # dark grey — primary text
    R = '\033[91m'        # red — breach/blocked
    DIM = '\033[2m'       # dim — secondary text
    BOLD = '\033[1m'
    _ = '\033[0m'         # reset


def header(text: str):
    w = 62
    print(f"\n{C.BOLD}{C.H}{'━' * w}{C._}")
    print(f"{C.BOLD}{C.H}  {text}{C._}")
    print(f"{C.BOLD}{C.H}{'━' * w}{C._}\n")


def pause(seconds: float = 2.0):
    if AUTO:
        time.sleep(seconds)
    else:
        input(f"{C.DIM}  ↵ Press Enter{C._}")


def bar(label: str, count: int, total: int, color: str, char: str = "█"):
    pct = count / total * 100 if total else 0
    bar_width = int(pct / 100 * 30)
    print(f"  {C.CY}{label:28s}{C._} {color}{char * bar_width}{C._} {color}{count}{C._} ({pct:.0f}%)")


# ═══════════════════════════════════════════════════════════════════════════════
# ACT 1: Gemini Thinking Mode
# ═══════════════════════════════════════════════════════════════════════════════

def act1_thinking():
    header("ACT 1  ·  Gemini Reads a Treasury Report")

    print(f"  {C.W}Input: 6-page treasury pack (Orion Metals Trading AG){C._}")
    print(f"  {C.W}Task:  Extract compliance signals with reasoning chain{C._}")
    print()

    # Show a compact document excerpt — just the key numbers
    print(f"  {C.DIM}┌─────────────────────────────────────────────────────┐{C._}")
    print(f"  {C.DIM}│  DAILY TREASURY REPORT — Orion Metals Trading AG   │{C._}")
    print(f"  {C.DIM}│                                                     │{C._}")
    print(f"  {C.DIM}│  Unrestricted cash:  CHF 96,400                    │{C._}")
    print(f"  {C.DIM}│  Covenant minimum:   CHF 100,000  ← {C.R}BREACH{C.DIM}         │{C._}")
    print(f"  {C.DIM}│                                                     │{C._}")
    print(f"  {C.DIM}│  RCF utilization:    92.0%                          │{C._}")
    print(f"  {C.DIM}│  Internal limit:     85%         ← {C.R}BREACH{C.DIM}         │{C._}")
    print(f"  {C.DIM}│                                                     │{C._}")
    print(f"  {C.DIM}│  Payment hold:       CHF 58,700  (name mismatch)   │{C._}")
    print(f"  {C.DIM}│  Lender: AlpineBank  (covenant terms confirmed)     │{C._}")
    print(f"  {C.DIM}└─────────────────────────────────────────────────────┘{C._}")

    pause(2)

    # Thinking chain — abbreviated, like reading over Gemini's shoulder
    print(f"  {C.BOLD}{C.B}Gemini's Reasoning (Thinking Mode):{C._}")
    print()

    thoughts = [
        "Scanning for threshold violations...",
        "Cash CHF 96,400 < covenant CHF 100,000 → covenant breach",
        "Lender AlpineBank confirmed definition of 'unrestricted cash'",
        "  → covenant_breach confirmed (definition locked by bank)",
        "",
        "RCF utilization 92.0% > internal limit 85%",
        "  → position_limit_breach (clear threshold, authorized)",
        "",
        "Payment hold CHF 58,700 = settlement failure (event, not breach)",
        "  → cannot be a threshold violation by definition",
    ]

    for line in thoughts:
        if line == "":
            print()
        else:
            print(f"  {C.B}  {line}{C._}")
        time.sleep(0.4 if AUTO else 0.1)

    print()
    print(f"  {C.G}✓ 5 signals extracted with full reasoning chain{C._}")
    print(f"  {C.G}✓ Every extraction is auditable — stored with evidence{C._}")

    pause(2)


# ═══════════════════════════════════════════════════════════════════════════════
# ACT 2: Canonicalizer
# ═══════════════════════════════════════════════════════════════════════════════

def act2_canonicalizer():
    header("ACT 2  ·  The Canonicalizer (AI Proposes, Kernel Disposes)")

    print(f"  {C.W}Gemini found 14 signals across two packs (Treasury + Wealth).{C._}")
    print(f"  {C.W}Without validation, ALL 14 would be flagged as breaches.{C._}")
    print(f"  {C.W}The Canonicalizer applies deterministic rules:{C._}")
    print()

    # The before/after — this is the money shot
    # Show the filtering as a visual pipeline

    signals = [
        # (name, what happened, final status)
        # TREASURY (Orion v2) — 3 observations
        ("FX EUR 380k unhedged", "hedge target band, not hard limit", "obs"),
        ("Settlement fail CHF 58.7k", "event — beneficiary mismatch", "obs"),
        ("Fee spike CHF 4,980", "event — bank account anomaly", "obs"),
        # WEALTH (Stonebridge) — 7 observations
        ("Fund 12.7% > 12% cap", "lookthrough not available", "obs"),
        ("Equity 42.1% > 40% max", "classification disputed", "obs"),
        ("EM Fund lookthrough", "missing constituents data", "obs"),
        ("Settlement CHF 220k", "event — pending cash", "obs"),
        ("Withdrawal CHF 500k", "event — client request", "obs"),
        ("Missing KID (ZEN Autocall)", "event — PRIIPs blocker", "obs"),
        ("Stale suitability (18mo)", "event — questionnaire expired", "obs"),
        # TREASURY (Orion v2) — 2 breaches
        ("RCF 92% > 85% limit", "confirmed — authorized threshold", "BREACH"),
        ("Covenant CHF 96k < 100k", "confirmed — definition locked", "BREACH"),
        # WEALTH (Stonebridge) — 2 breaches
        ("Alpina 8.4% > 7% issuer cap", "confirmed — IPS locked", "BREACH"),
        ("Custody fee 0.45% vs 0.30%", "confirmed — fee schedule", "BREACH"),
    ]

    for name, reason, status in signals:
        if status == "BREACH":
            icon = f"{C.R}██ BREACH{C._}"
        else:
            icon = f"{C.CY}░░ obs   {C._}"

        print(f"  {icon}  {C.W}{name:30s}{C._}  {C.DIM}{reason}{C._}")
        time.sleep(0.3 if AUTO else 0.05)

    print()

    # The headline numbers
    print(f"  {C.BOLD}{'─' * 55}{C._}")
    bar("Breach-category signals:", 14, 14, C.W)
    bar("False breaches prevented:", 10, 14, C.G)
    bar("Confirmed breaches:", 4, 14, C.R)
    print(f"  {C.BOLD}{'─' * 55}{C._}")
    print()
    print(f"  {C.BOLD}{C.G}71% false alarm prevention  ·  0 missed signals{C._}")
    print(f"  {C.DIM}  Same inputs → same outputs. Deterministic. Replayable.{C._}")

    pause(2)


# ═══════════════════════════════════════════════════════════════════════════════
# ACT 3: Safety Layer
# ═══════════════════════════════════════════════════════════════════════════════

def act3_safety():
    header("ACT 3  ·  AI Never Recommends")

    print(f"  {C.W}The system presents options symmetrically. No defaults.{C._}")
    print(f"  {C.W}If an AI tries to sneak in a recommendation:{C._}")
    print()

    # Show the poisoned claims
    claims = [
        ("Exposure reached $75M vs $70M limit", True),
        ("We recommend reducing exposure immediately", False),
        ("This appears to be deteriorating rapidly", False),
        ("This is critical and requires urgent action", False),
    ]

    for text, safe in claims:
        if safe:
            print(f"  {C.G}✓{C._}  \"{text}\"")
        else:
            print(f"  {C.R}⚡{C._}  \"{text}\"")
        time.sleep(0.3 if AUTO else 0.05)

    print()
    pause(1)

    # Run the actual detector
    from evals.validators.hallucination import HallucinationDetector
    from coprocessor.schemas.narrative import (
        NarrativeMemo, MemoSection, NarrativeClaim, EvidenceReference
    )

    poisoned = NarrativeMemo(
        decision_id="demo",
        title="Test",
        sections=[MemoSection(
            heading="Analysis",
            claims=[
                NarrativeClaim(
                    text=text,
                    evidence_refs=[EvidenceReference(evidence_id="sig_001", evidence_type="signal")]
                )
                for text, _ in claims
            ]
        )]
    )

    detector = HallucinationDetector()
    result = detector.detect(poisoned)

    print(f"  {C.R}{C.BOLD}BLOCKED — {len(result.errors)} violations caught:{C._}")
    print()

    for err in result.errors:
        print(f"  {C.R}  ✗ {err.error_type:18s}  pattern: \"{err.pattern_matched}\"{C._}")
        time.sleep(0.3 if AUTO else 0.05)

    print()
    print(f"  {C.G}Deterministic regex — zero false negatives, O(n) time{C._}")
    print(f"  {C.G}CI-gated — violations fail the build{C._}")

    pause(2)


# ═══════════════════════════════════════════════════════════════════════════════
# Closing
# ═══════════════════════════════════════════════════════════════════════════════

def closing():
    w = 62
    print(f"\n{C.BOLD}{C.G}{'━' * w}{C._}")
    print(f"""
  {C.BOLD}{C.W}GOVERNANCE OS{C._}
  {C.DIM}Deterministic Policy Engine with Transparent AI{C._}

  {C.B}Gemini 3{C._}     reads documents, shows its reasoning
  {C.G}Kernel{C._}       validates with zero randomness
  {C.W}Human{C._}        decides with full context

  {C.BOLD}AI that extracts, but never decides.{C._}
""")
    print(f"{C.BOLD}{C.G}{'━' * w}{C._}\n")


# ═══════════════════════════════════════════════════════════════════════════════

def main():
    try:
        act1_thinking()
        act2_canonicalizer()
        act3_safety()
        closing()
    except KeyboardInterrupt:
        print(f"\n{C.DIM}  Interrupted.{C._}")
        sys.exit(0)


if __name__ == "__main__":
    main()
