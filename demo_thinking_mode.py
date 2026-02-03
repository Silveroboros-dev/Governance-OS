#!/usr/bin/env python3
"""
Demo: Gemini 3 Thinking Mode for Transparent AI Reasoning (Hack D)

This demo shows how Governance OS uses Gemini's Thinking Mode to provide
audit-grade transparency into WHY the AI extracted specific signals.

For hackathon video recording:
    make demo-thinking-auto

Interactive mode:
    make demo-thinking
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.RESET}\n")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}>>> {title}{Colors.RESET}")
    print(f"{Colors.DIM}{'-'*50}{Colors.RESET}")


def print_document(text: str):
    print(f"{Colors.DIM}")
    for line in text.strip().split('\n'):
        print(f"  {line}")
    print(f"{Colors.RESET}")


def print_thinking(thoughts: str):
    """Print Gemini's thinking process with formatting."""
    print(f"{Colors.YELLOW}")
    print("  [Gemini's Reasoning Chain]")
    print()
    for line in thoughts.strip().split('\n'):
        print(f"  {line}")
    print(f"{Colors.RESET}")


def print_signal(signal: dict, index: int):
    """Print an extracted signal."""
    conf = signal.get('confidence', 0)
    conf_color = Colors.GREEN if conf >= 0.9 else Colors.YELLOW if conf >= 0.7 else Colors.RED

    print(f"\n  {Colors.BOLD}Signal #{index + 1}:{Colors.RESET} {signal.get('signal_type', 'unknown')}")
    print(f"  {Colors.DIM}Confidence:{Colors.RESET} {conf_color}{conf:.0%}{Colors.RESET}")

    if signal.get('payload'):
        print(f"  {Colors.DIM}Payload:{Colors.RESET}")
        for k, v in signal['payload'].items():
            print(f"    - {k}: {v}")

    if signal.get('source_spans'):
        span = signal['source_spans'][0]
        print(f"  {Colors.DIM}Source:{Colors.RESET} \"{span.get('text', '')[:50]}...\"")


def run_demo(auto_mode: bool = False):
    """Run the Thinking Mode demo."""

    print_header("Gemini 3 Thinking Mode Demo")
    print(f"{Colors.BOLD}Hack D: Transparent AI Reasoning for Audit-Grade Evidence{Colors.RESET}")
    print()
    print("This demo shows how Governance OS exposes Gemini's reasoning")
    print("chain, enabling compliance review of AI decision-making.")

    if not auto_mode:
        input(f"\n{Colors.DIM}Press Enter to continue...{Colors.RESET}")
    else:
        time.sleep(2)

    # Sample treasury document
    sample_document = """
    DAILY TREASURY REPORT - January 15, 2025

    POSITION SUMMARY:
    - EUR/USD exposure: $45.2M (limit: $40M) - BREACH
    - GBP/USD exposure: $28.1M (limit: $35M) - OK

    COUNTERPARTY UPDATES:
    - Acme Bank credit rating downgraded from A to BBB+ by S&P
    - Current exposure to Acme Bank: $12.5M

    LIQUIDITY:
    - Operating cash: $8.2M
    - Minimum threshold: $10M
    - Status: BELOW THRESHOLD

    Prepared by: J. Smith, Treasury Operations
    """

    print_section("Step 1: Input Document")
    print("Treasury report with multiple signals to extract:")
    print_document(sample_document)

    if not auto_mode:
        input(f"\n{Colors.DIM}Press Enter to extract signals with Thinking Mode...{Colors.RESET}")
    else:
        time.sleep(2)

    print_section("Step 2: Gemini Processes with Thinking Mode")
    print(f"{Colors.CYAN}Calling IntakeAgent with thinking_level='high'...{Colors.RESET}")

    # Check if we have API key
    if not os.environ.get("GOOGLE_API_KEY"):
        print(f"\n{Colors.YELLOW}Note: GOOGLE_API_KEY not set. Showing simulated output.{Colors.RESET}")

        # Simulated thinking output
        simulated_thoughts = """
I need to extract structured signals from this treasury report.

First, I'll scan for position limit breaches:
- EUR/USD at $45.2M exceeds the $40M limit - this is a clear breach
- GBP/USD at $28.1M is within the $35M limit - no breach

Next, checking for counterparty events:
- Acme Bank downgraded from A to BBB+ - this is a significant
  credit event that requires a counterparty_credit_downgrade signal
- Exposure is $12.5M which should be included in the signal

Finally, liquidity status:
- Operating cash $8.2M is below the $10M threshold
- This triggers a liquidity_threshold_breach signal

I'm confident in these three signals as each has explicit
numerical data with clear threshold comparisons in the source text.
        """

        simulated_signals = [
            {
                "signal_type": "fx_exposure_breach",
                "confidence": 0.95,
                "payload": {
                    "currency_pair": "EUR/USD",
                    "exposure_amount": 45200000,
                    "limit_amount": 40000000,
                    "breach_amount": 5200000
                },
                "source_spans": [{"text": "EUR/USD exposure: $45.2M (limit: $40M) - BREACH"}]
            },
            {
                "signal_type": "counterparty_credit_downgrade",
                "confidence": 0.92,
                "payload": {
                    "counterparty": "Acme Bank",
                    "old_rating": "A",
                    "new_rating": "BBB+",
                    "rating_agency": "S&P",
                    "exposure_amount": 12500000
                },
                "source_spans": [{"text": "Acme Bank credit rating downgraded from A to BBB+ by S&P"}]
            },
            {
                "signal_type": "liquidity_threshold_breach",
                "confidence": 0.94,
                "payload": {
                    "current_amount": 8200000,
                    "threshold_amount": 10000000,
                    "shortfall": 1800000
                },
                "source_spans": [{"text": "Operating cash: $8.2M, Minimum threshold: $10M, Status: BELOW THRESHOLD"}]
            }
        ]

        time.sleep(1 if auto_mode else 0)

        print_section("Step 3: Gemini's Reasoning Chain (Thinking Mode)")
        print_thinking(simulated_thoughts)

        if not auto_mode:
            input(f"\n{Colors.DIM}Press Enter to see extracted signals...{Colors.RESET}")
        else:
            time.sleep(2)

        print_section("Step 4: Extracted Signals")
        for i, signal in enumerate(simulated_signals):
            print_signal(signal, i)

    else:
        # Real API call
        try:
            from coprocessor.agents.intake_agent import IntakeAgent

            agent = IntakeAgent(use_thinking=True, thinking_level="high")
            result = agent.extract_signals_sync(
                content=sample_document,
                pack="treasury",
                document_source="demo_treasury_report.txt",
            )

            if result.thinking_summary:
                print_section("Step 3: Gemini's Reasoning Chain (Thinking Mode)")
                print_thinking(result.thinking_summary)

            if not auto_mode:
                input(f"\n{Colors.DIM}Press Enter to see extracted signals...{Colors.RESET}")
            else:
                time.sleep(2)

            print_section("Step 4: Extracted Signals")
            for i, candidate in enumerate(result.candidates):
                print_signal({
                    "signal_type": candidate.signal_type,
                    "confidence": candidate.confidence,
                    "payload": candidate.payload,
                    "source_spans": [{"text": s.text} for s in candidate.source_spans]
                }, i)

        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
            print(f"{Colors.YELLOW}Falling back to simulated output...{Colors.RESET}")
            return run_demo(auto_mode)

    # Summary
    print_section("Why This Matters")
    print(f"""
{Colors.BOLD}Audit-Grade Transparency:{Colors.RESET}
  - Compliance officers can review WHY signals were extracted
  - Reasoning chain is stored with evidence pack
  - Enables AI governance and explainability requirements

{Colors.BOLD}Gemini 3 Features Used:{Colors.RESET}
  - Thinking Mode (include_thoughts=True, thinking_level='high')
  - Context Caching (90% cost reduction)
  - Native JSON Mode (guaranteed valid output)

{Colors.BOLD}The Result:{Colors.RESET}
  Deterministic governance kernel + transparent AI coprocessor
  = Enterprise-ready AI for high-stakes decisions
""")

    print_header("Demo Complete")
    print(f"{Colors.GREEN}Hack D: Thinking Mode provides audit-grade AI transparency{Colors.RESET}\n")


if __name__ == "__main__":
    auto_mode = "--auto" in sys.argv or "-a" in sys.argv
    run_demo(auto_mode=auto_mode)
