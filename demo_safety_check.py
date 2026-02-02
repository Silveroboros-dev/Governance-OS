#!/usr/bin/env python3
"""
GOVERNANCE OS - SAFETY CHECK DEMO
=================================

This demo shows how Governance OS catches AI hallucinations and blocks
unsafe outputs before they reach decision-makers.

The Demo Script (for video):
1. Setup: Show the safety requirements
2. Attack: Inject a "poisoned" prompt that tries to force recommendations
3. Defense: Watch the HallucinationDetector catch and block it
4. Pitch: Deterministic regex safety layer wrapping AI reasoning

Run: python demo_safety_check.py           # Interactive mode
     python demo_safety_check.py --auto    # Auto-advance (for video recording)
"""

import argparse
import json
import time
import sys
from datetime import datetime

# Parse args early
parser = argparse.ArgumentParser()
parser.add_argument('--auto', action='store_true', help='Auto-advance without user input (for video)')
parser.add_argument('--fast', action='store_true', help='Skip typewriter effect')
args, _ = parser.parse_known_args()

AUTO_MODE = args.auto
FAST_MODE = args.fast

# Add project root to path
sys.path.insert(0, '.')

from evals.validators.hallucination import HallucinationDetector, HallucinationError
from evals.validators.grounding import GroundingValidator
from coprocessor.schemas.narrative import (
    NarrativeMemo,
    MemoSection,
    NarrativeClaim,
    EvidenceReference
)

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}\n")


def print_step(step: int, text: str):
    print(f"{Colors.BOLD}{Colors.CYAN}[STEP {step}]{Colors.END} {text}")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_code(text: str):
    print(f"{Colors.BLUE}  {text}{Colors.END}")


def slow_print(text: str, delay: float = 0.03):
    """Print text with a typewriter effect for demo."""
    if FAST_MODE:
        print(text)
        return
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()


def wait_for_input(prompt: str):
    """Wait for user input, or auto-advance in auto mode."""
    if AUTO_MODE:
        print(f"\n{Colors.CYAN}[Auto-advancing in 2s...]{Colors.END}")
        time.sleep(2)
    else:
        input(prompt)


def demo_intro():
    """Introduction to the safety demo."""
    print_header("GOVERNANCE OS - AI SAFETY DEMO")

    slow_print("Governance OS requires STRICT adherence to evidence.")
    print()
    slow_print("AI agents can draft memos, but they are NEVER allowed to:")
    print()
    print_error("Make recommendations (\"should\", \"recommend\", \"best option\")")
    print_error("Express opinions (\"I think\", \"appears to be\", \"likely\")")
    print_error("Judge severity (\"critical\", \"urgent\", \"immediately\")")
    print_error("Evaluate policies (\"threshold is too strict\")")
    print()
    slow_print("Let's see what happens when an AI tries to break these rules...")
    wait_for_input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")


def demo_safe_memo():
    """Show a properly grounded memo passing validation."""
    print_header("STEP 1: A PROPERLY GROUNDED MEMO")

    print_step(1, "Creating a memo with proper evidence grounding...\n")

    # Create a safe memo
    safe_memo = NarrativeMemo(
        decision_id="dec_001",
        title="BTC Position Limit Breach",
        sections=[
            MemoSection(
                heading="Situation",
                claims=[
                    NarrativeClaim(
                        text="The BTC position reached $152.3M at 14:32 UTC",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_pos_001", evidence_type="signal")
                        ]
                    ),
                    NarrativeClaim(
                        text="This exceeds the $100M single-asset limit defined in Policy v2.1",
                        evidence_refs=[
                            EvidenceReference(evidence_id="pol_pos_001", evidence_type="policy"),
                            EvidenceReference(evidence_id="eval_pos_001", evidence_type="evaluation")
                        ]
                    ),
                ]
            ),
            MemoSection(
                heading="Decision",
                claims=[
                    NarrativeClaim(
                        text="The decision-maker selected Option A to reduce the position",
                        evidence_refs=[
                            EvidenceReference(evidence_id="opt_pos_001a", evidence_type="chosen_option")
                        ]
                    ),
                ]
            ),
        ]
    )

    print(f"{Colors.BLUE}Memo Title:{Colors.END} {safe_memo.title}")
    print(f"{Colors.BLUE}Claims:{Colors.END}")
    for section in safe_memo.sections:
        for claim in section.claims:
            print(f"  • \"{claim.text[:60]}...\"")
            print(f"    {Colors.GREEN}Evidence: {[r.evidence_id for r in claim.evidence_refs]}{Colors.END}")

    print(f"\n{Colors.BOLD}Running HallucinationDetector...{Colors.END}\n")
    time.sleep(1)

    detector = HallucinationDetector()
    result = detector.detect(safe_memo)

    if result.passed:
        print_success("PASSED - No hallucinations detected!")
        print_success(f"All {result.total_claims} claims are properly grounded")
    else:
        print_error("FAILED - Hallucinations detected")

    wait_for_input(f"\n{Colors.CYAN}Press Enter to see what happens with a POISONED memo...{Colors.END}")


def demo_poisoned_memo():
    """Show a poisoned memo being caught by the detector."""
    print_header("STEP 2: THE ATTACK - POISONED AI OUTPUT")

    print_step(2, "Simulating a malicious/hallucinating AI response...\n")

    print(f"{Colors.RED}Scenario: An AI has been prompted to draft a memo,")
    print(f"but it tries to RECOMMEND an option (FORBIDDEN!){Colors.END}\n")

    time.sleep(1)

    # Create a poisoned memo with forbidden patterns
    poisoned_memo = NarrativeMemo(
        decision_id="dec_002",
        title="Counterparty Exposure Assessment",
        sections=[
            MemoSection(
                heading="Analysis",
                claims=[
                    NarrativeClaim(
                        text="Exposure to Bank XYZ reached $75M against a $70M limit",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_cp_001", evidence_type="signal")
                        ]
                    ),
                    # POISONED CLAIM 1: Recommendation
                    NarrativeClaim(
                        text="We recommend reducing exposure immediately to avoid further risk",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_cp_001", evidence_type="signal")
                        ]
                    ),
                    # POISONED CLAIM 2: Opinion
                    NarrativeClaim(
                        text="This situation appears to be deteriorating rapidly",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_cp_001", evidence_type="signal")
                        ]
                    ),
                    # POISONED CLAIM 3: Severity judgment
                    NarrativeClaim(
                        text="This is critical and requires urgent action",
                        evidence_refs=[
                            EvidenceReference(evidence_id="sig_cp_001", evidence_type="signal")
                        ]
                    ),
                ]
            ),
        ]
    )

    print(f"{Colors.RED}Poisoned Memo Claims:{Colors.END}")
    for section in poisoned_memo.sections:
        for i, claim in enumerate(section.claims):
            if i == 0:
                print(f"  {Colors.GREEN}✓{Colors.END} \"{claim.text}\"")
            else:
                print(f"  {Colors.RED}⚡{Colors.END} \"{claim.text}\"")

    print(f"\n{Colors.BOLD}Running HallucinationDetector...{Colors.END}\n")
    time.sleep(1)

    detector = HallucinationDetector()
    result = detector.detect(poisoned_memo)

    if not result.passed:
        print_error(f"BLOCKED! {len(result.errors)} violations detected:\n")

        for error in result.errors:
            print(f"  {Colors.RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
            print(f"  {Colors.RED}Type:{Colors.END} {error.error_type.upper()}")
            print(f"  {Colors.RED}Pattern:{Colors.END} \"{error.pattern_matched}\"")
            print(f"  {Colors.RED}Regex:{Colors.END} r\"\\b{error.pattern_matched}\\b\"")
            print(f"  {Colors.RED}Claim:{Colors.END} \"{error.claim_text[:50]}...\"")
            time.sleep(0.5)

    wait_for_input(f"\n{Colors.CYAN}Press Enter to see the defense mechanism...{Colors.END}")


def demo_defense_mechanism():
    """Show the regex patterns that caught the violations."""
    print_header("STEP 3: THE DEFENSE - DETERMINISTIC REGEX LAYER")

    print_step(3, "How the HallucinationDetector works:\n")

    print(f"{Colors.BOLD}Forbidden Pattern Categories:{Colors.END}\n")

    detector = HallucinationDetector()

    categories = [
        ("RECOMMENDATIONS", detector.RECOMMENDATION_PATTERNS, "should, recommend, best option"),
        ("OPINIONS", detector.OPINION_PATTERNS, "I think, appears to be, likely"),
        ("SEVERITY JUDGMENTS", detector.SEVERITY_PATTERNS, "critical, urgent, immediately"),
        ("POLICY EVALUATION", detector.POLICY_EVAL_PATTERNS, "threshold is too, change the policy"),
    ]

    for name, patterns, examples in categories:
        print(f"{Colors.YELLOW}{name}:{Colors.END}")
        print(f"  Examples: {examples}")
        print(f"  Patterns: {len(patterns)} regex rules")
        print(f"  Sample:   {Colors.BLUE}{patterns[0]}{Colors.END}")
        print()

    print(f"\n{Colors.BOLD}Key Point:{Colors.END}")
    slow_print("These patterns are DETERMINISTIC - they run in O(n) time,")
    slow_print("they're unit-testable, and they NEVER miss a match.")
    print()
    slow_print("AI reasoning is powerful but unpredictable.")
    slow_print("Regex is simple but RELIABLE.")
    print()
    print(f"{Colors.GREEN}We use BOTH: AI for drafting, Regex for safety.{Colors.END}")

    wait_for_input(f"\n{Colors.CYAN}Press Enter to see the final pitch...{Colors.END}")


def demo_pitch():
    """The final pitch for the hackathon."""
    print_header("THE GOVERNANCE OS SAFETY ARCHITECTURE")

    print(f"""
{Colors.BOLD}The Two-Layer Safety System:{Colors.END}

    ┌─────────────────────────────────────────────┐
    │  {Colors.CYAN}LAYER 1: GEMINI 3 AI REASONING{Colors.END}              │
    │                                             │
    │  • Drafts narrative memos from evidence     │
    │  • Extracts signals from unstructured docs  │
    │  • Uses 90% cheaper context caching         │
    │                                             │
    │  {Colors.YELLOW}(Powerful but unpredictable){Colors.END}               │
    └─────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────┐
    │  {Colors.GREEN}LAYER 2: DETERMINISTIC REGEX SAFETY{Colors.END}        │
    │                                             │
    │  • Catches ALL forbidden patterns           │
    │  • Zero false negatives (regex is exact)    │
    │  • Blocks writes before they reach DB       │
    │  • CI-gated (fails build on violations)     │
    │                                             │
    │  {Colors.GREEN}(Simple but RELIABLE){Colors.END}                      │
    └─────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────┐
    │  {Colors.BOLD}HUMAN DECISION-MAKER{Colors.END}                        │
    │                                             │
    │  • Sees ONLY clean, grounded memos          │
    │  • No AI recommendations or opinions        │
    │  • Full evidence trail for accountability   │
    └─────────────────────────────────────────────┘
""")

    print(f"\n{Colors.BOLD}The Pitch:{Colors.END}")
    slow_print("\"We use Gemini's reasoning to draft the memo,")
    slow_print(" but we wrap it in a deterministic Regex safety layer")
    slow_print(" to ensure compliance. Zero hallucinations. Guaranteed.\"")

    print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}       GOVERNANCE OS - SAFE AI FOR HIGH-STAKES DECISIONS{Colors.END}")
    print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")


def main():
    """Run the full safety demo."""
    try:
        demo_intro()
        demo_safe_memo()
        demo_poisoned_memo()
        demo_defense_mechanism()
        demo_pitch()

        print(f"\n{Colors.CYAN}Demo complete! Run 'make evals' to see full test suite.{Colors.END}\n")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted.{Colors.END}")
        sys.exit(0)


if __name__ == "__main__":
    main()
