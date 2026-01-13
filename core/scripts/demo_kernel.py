"""
Demo script for the Governance OS kernel.

Demonstrates the full governance loop:
Signal → Policy Evaluation → Exception → Decision → Evidence Pack
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parents[2]))

from datetime import datetime
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import PolicyVersion, Signal, ExceptionStatus
from core.services import PolicyEngine, Evaluator, ExceptionEngine, DecisionRecorder, EvidenceGenerator


def demo_full_loop():
    """Demonstrate full governance kernel loop."""
    print("=" * 70)
    print("Governance OS - Kernel Demo")
    print("Full Loop: Signal → Evaluation → Exception → Decision → Evidence")
    print("=" * 70)
    print()

    db = SessionLocal()

    try:
        # Step 1: Get active policies
        print("[Step 1] Loading active policies...")
        policy_engine = PolicyEngine(db)
        policies = policy_engine.get_active_policies("treasury")

        if not policies:
            print("  ERROR: No active policies found. Run 'make seed' first.")
            return

        print(f"  Found {len(policies)} active treasury policies")
        for policy in policies:
            print(f"    - {policy.policy.name} (v{policy.version_number})")
        print()

        # Step 2: Get recent signals
        print("[Step 2] Loading recent signals...")
        signals = (
            db.query(Signal)
            .filter(Signal.pack == "treasury")
            .order_by(Signal.observed_at.desc())
            .limit(10)
            .all()
        )

        if not signals:
            print("  ERROR: No signals found. Run 'make seed' first.")
            return

        print(f"  Found {len(signals)} recent signals")
        for signal in signals[:3]:
            print(f"    - {signal.signal_type} (observed {signal.observed_at})")
        print()

        # Step 3: Run evaluations
        print("[Step 3] Running policy evaluations...")
        evaluator = Evaluator(db)
        exception_engine = ExceptionEngine(db)
        evaluations = []
        exceptions = []

        for policy_version in policies:
            evaluation = evaluator.evaluate(policy_version, signals)
            evaluations.append(evaluation)

            print(f"  Evaluated: {policy_version.policy.name}")
            print(f"    Result: {evaluation.result.value}")
            print(f"    Hash: {evaluation.input_hash[:16]}...")

            # Generate exception if needed
            exception = exception_engine.generate_exception(evaluation, policy_version)
            if exception:
                exceptions.append(exception)
                print(f"    Exception raised: {exception.severity.value}")
            print()

        # Step 4: List open exceptions
        print(f"[Step 4] Open exceptions: {len(exceptions)}")
        if not exceptions:
            print("  No exceptions raised. All evaluations passed!")
            print()
            return

        for exc in exceptions:
            print(f"  - {exc.title}")
            print(f"    Severity: {exc.severity.value}")
            print(f"    Options: {len(exc.options)}")
        print()

        # Step 5: Record decision for first exception
        if exceptions:
            exception = exceptions[0]
            print(f"[Step 5] Recording decision for: {exception.title}")

            recorder = DecisionRecorder(db)
            chosen_option = exception.options[0]

            decision = recorder.record_decision(
                exception_id=exception.id,
                chosen_option_id=chosen_option["id"],
                rationale=f"Demo decision: Choosing '{chosen_option['label']}' for demonstration purposes. "
                          f"This decision was made by the demo script to show the full kernel loop.",
                decided_by="demo_script",
                assumptions="This is a demo decision with synthetic data"
            )

            print(f"  Decision recorded: {decision.id}")
            print(f"  Chosen option: {chosen_option['label']}")
            print(f"  Decided at: {decision.decided_at}")
            print()

            # Step 6: Generate evidence pack
            print("[Step 6] Generating evidence pack...")
            evidence_gen = EvidenceGenerator(db)
            evidence_pack = evidence_gen.generate_pack(decision)

            print(f"  Evidence pack generated: {evidence_pack.id}")
            print(f"  Content hash: {evidence_pack.content_hash[:16]}...")
            print(f"  Generated at: {evidence_pack.generated_at}")
            print()

            # Step 7: Verify evidence pack structure
            print("[Step 7] Evidence pack contents:")
            print(f"  - Decision: {evidence_pack.evidence['decision']['rationale'][:50]}...")
            print(f"  - Exception: {evidence_pack.evidence['exception']['title']}")
            print(f"  - Evaluation: {evidence_pack.evidence['evaluation']['result']}")
            print(f"  - Policy: {evidence_pack.evidence['policy']['name']}")
            print(f"  - Signals: {len(evidence_pack.evidence['signals'])} signals")
            print(f"  - Audit trail: {len(evidence_pack.evidence['audit_trail'])} events")
            print()

        print("=" * 70)
        print("Demo completed successfully!")
        print()
        print("Full governance loop demonstrated:")
        print("  ✓ Signals ingested")
        print("  ✓ Policies evaluated (deterministic)")
        print("  ✓ Exceptions raised (with deduplication)")
        print("  ✓ Decisions recorded (immutable)")
        print("  ✓ Evidence packs generated (audit-grade)")
        print()
        print("Access the API at: http://localhost:8000/docs")
        print("=" * 70)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    demo_full_loop()
