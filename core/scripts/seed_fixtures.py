"""
Seed script for loading pack fixtures (Treasury and Wealth).

Loads policies and sample signals for demonstration.
Supports loading scenarios from fixtures/scenarios.json.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parents[2]))

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine, Base
from core.models import Policy, PolicyVersion, PolicyStatus, Signal, SignalReliability
from core.services import PolicyEngine, Evaluator, ExceptionEngine
from packs.treasury.policy_templates import TREASURY_POLICY_TEMPLATES
from packs.wealth.policy_templates import WEALTH_POLICY_TEMPLATES

# Paths to scenarios files
PACKS_PATH = Path(__file__).parents[2] / "packs"
TREASURY_SCENARIOS_PATH = PACKS_PATH / "treasury" / "fixtures" / "scenarios.json"
WEALTH_SCENARIOS_PATH = PACKS_PATH / "wealth" / "fixtures" / "scenarios.json"

# Pack configurations
PACK_CONFIGS = {
    "treasury": {
        "templates": TREASURY_POLICY_TEMPLATES,
        "scenarios_path": TREASURY_SCENARIOS_PATH,
    },
    "wealth": {
        "templates": WEALTH_POLICY_TEMPLATES,
        "scenarios_path": WEALTH_SCENARIOS_PATH,
    },
}


def seed_policies(db: Session, pack: str = None):
    """Seed policies for specified pack(s)."""
    packs_to_seed = [pack] if pack else list(PACK_CONFIGS.keys())

    for pack_name in packs_to_seed:
        if pack_name not in PACK_CONFIGS:
            print(f"Unknown pack: {pack_name}")
            continue

        templates = PACK_CONFIGS[pack_name]["templates"]
        print(f"Seeding {pack_name} policies...")

        for key, template in templates.items():
            # Check if policy exists
            existing = db.query(Policy).filter(
                Policy.name == template["name"],
                Policy.pack == pack_name
            ).first()

            if existing:
                print(f"  Policy '{template['name']}' already exists, skipping")
                continue

            # Create policy
            policy = Policy(
                name=template["name"],
                pack=pack_name,
                description=template["description"],
                created_by="system_seed"
            )
            db.add(policy)
            db.flush()

            # Create version 1
            policy_version = PolicyVersion(
                policy_id=policy.id,
                version_number=1,
                status=PolicyStatus.ACTIVE,
                rule_definition=template["rule_definition"],
                valid_from=datetime.now(timezone.utc) - timedelta(days=30),
                valid_to=None,
                changelog="Initial version",
                created_by="system_seed"
            )
            db.add(policy_version)

            print(f"  Created policy: {template['name']}")

        db.commit()
        print(f"{pack_name.capitalize()} policies seeded successfully\n")


def seed_signals(db: Session, pack: str = None):
    """Seed sample signals (basic set) for specified pack(s)."""
    packs_to_seed = [pack] if pack else ["treasury"]  # Basic signals only for treasury

    if "treasury" in packs_to_seed:
        print("Seeding basic treasury signals...")

        # Signal 1: BTC position limit breach (high severity - 2 hours duration)
        signal1 = Signal(
            pack="treasury",
            signal_type="position_limit_breach",
            payload={
                "asset": "BTC",
                "current_position": 120,
                "limit": 100,
                "duration_hours": 2
            },
            source="risk_monitoring_system",
            reliability=SignalReliability.HIGH,
            observed_at=datetime.now(timezone.utc) - timedelta(hours=2),
            signal_metadata={"system": "risk_dashboard", "alert_id": "BTC_001"}
        )
        db.add(signal1)

        # Signal 2: ETH volatility spike
        signal2 = Signal(
            pack="treasury",
            signal_type="market_volatility_spike",
            payload={
                "asset": "ETH",
                "volatility": 0.45,
                "threshold": 0.30,
                "window_hours": 24
            },
            source="market_data_provider",
            reliability=SignalReliability.HIGH,
            observed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            signal_metadata={"provider": "bloomberg", "confidence": 0.95}
        )
        db.add(signal2)

        # Signal 3: Counterparty credit downgrade
        signal3 = Signal(
            pack="treasury",
            signal_type="counterparty_credit_downgrade",
            payload={
                "counterparty": "Exchange A",
                "previous_rating": "A",
                "new_rating": "BBB",
                "exposure_usd": 5000000
            },
            source="credit_rating_service",
            reliability=SignalReliability.HIGH,
            observed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            signal_metadata={"rating_agency": "S&P", "report_id": "CR2026001"}
        )
        db.add(signal3)

        # Signal 4: Lower severity position breach (< 1 hour)
        signal4 = Signal(
            pack="treasury",
            signal_type="position_limit_breach",
            payload={
                "asset": "SOL",
                "current_position": 5100,
                "limit": 5000,
                "duration_hours": 0.5
            },
            source="risk_monitoring_system",
            reliability=SignalReliability.HIGH,
            observed_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            signal_metadata={"system": "risk_dashboard", "alert_id": "SOL_001"}
        )
        db.add(signal4)

        db.commit()
        print(f"  Created 4 sample treasury signals")
        print("Treasury signals seeded successfully\n")

    # For wealth pack, use scenarios instead of basic signals
    if "wealth" in packs_to_seed and pack == "wealth":
        print("For wealth pack, use --scenarios to load realistic demo data")
        print("  Example: python -m core.scripts.seed_fixtures --pack=wealth --scenarios\n")


def seed_scenarios(db: Session, pack: str = None, scenario_ids: list[str] = None):
    """
    Seed signals from scenario definitions.

    Args:
        db: Database session
        pack: Pack to seed scenarios for. If None, seeds all packs.
        scenario_ids: List of scenario IDs to load. If None, loads all scenarios.
    """
    packs_to_seed = [pack] if pack else list(PACK_CONFIGS.keys())

    reliability_map = {
        "high": SignalReliability.HIGH,
        "medium": SignalReliability.MEDIUM,
        "low": SignalReliability.LOW
    }

    total_created = 0

    for pack_name in packs_to_seed:
        if pack_name not in PACK_CONFIGS:
            continue

        scenarios_path = PACK_CONFIGS[pack_name]["scenarios_path"]

        if not scenarios_path.exists():
            print(f"Scenarios file not found for {pack_name}: {scenarios_path}")
            continue

        print(f"Loading {pack_name} scenarios from fixtures...")

        with open(scenarios_path) as f:
            data = json.load(f)

        scenarios = data.get("scenarios", [])

        if scenario_ids:
            scenarios = [s for s in scenarios if s["id"] in scenario_ids]

        if not scenarios:
            print(f"  No matching scenarios found for {pack_name}")
            continue

        created_count = 0
        for scenario in scenarios:
            print(f"\n  Scenario: {scenario['name']}")
            narrative = scenario.get('narrative', scenario.get('description', ''))
            print(f"    {narrative[:100]}...")

            for signal_def in scenario.get("signals", []):
                signal = Signal(
                    pack=pack_name,
                    signal_type=signal_def["signal_type"],
                    payload=signal_def["payload"],
                    source=signal_def.get("source", "scenario_seed"),
                    reliability=reliability_map.get(
                        signal_def.get("reliability", "high"),
                        SignalReliability.HIGH
                    ),
                    observed_at=datetime.now(timezone.utc) - timedelta(minutes=15),
                    signal_metadata={
                        **signal_def.get("metadata", {}),
                        "scenario_id": scenario["id"],
                        "scenario_name": scenario["name"]
                    }
                )
                db.add(signal)
                created_count += 1
                print(f"    Created signal: {signal_def['signal_type']}")

        db.commit()
        total_created += created_count
        print(f"\n  Created {created_count} signals from {len(scenarios)} {pack_name} scenarios")

    print(f"Total scenarios seeded: {total_created} signals\n")


def trigger_evaluations(db: Session, pack: str = None):
    """Trigger policy evaluations to generate exceptions."""
    packs_to_evaluate = [pack] if pack else list(PACK_CONFIGS.keys())

    print("Triggering evaluations to generate exceptions...")
    print("-" * 40)

    for pack_name in packs_to_evaluate:
        if pack_name not in PACK_CONFIGS:
            continue

        # Get active policies for pack
        policy_engine = PolicyEngine(db)
        policies = policy_engine.get_active_policies(pack_name)

        if not policies:
            print(f"  No active policies for {pack_name}")
            continue

        # Get recent signals for pack (last 24 hours)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        signals = (
            db.query(Signal)
            .filter(
                Signal.pack == pack_name,
                Signal.observed_at >= since
            )
            .order_by(Signal.observed_at.desc())
            .all()
        )

        if not signals:
            print(f"  No recent signals for {pack_name}")
            continue

        print(f"\n  {pack_name.upper()}: Evaluating {len(policies)} policies against {len(signals)} signals")

        # Evaluate each policy
        evaluator = Evaluator(db)
        exception_engine = ExceptionEngine(db)
        exceptions_raised = 0

        for policy_version in policies:
            evaluation = evaluator.evaluate(policy_version, signals)
            exception = exception_engine.generate_exception(evaluation, policy_version)
            if exception:
                exceptions_raised += 1
                print(f"    Exception raised: {exception.title} ({exception.severity})")

        print(f"  {pack_name}: {exceptions_raised} exceptions raised")

    print("\n" + "-" * 40)
    print("Evaluations complete!\n")


def print_usage():
    """Print usage instructions."""
    print("Usage: python -m core.scripts.seed_fixtures [OPTIONS]")
    print()
    print("Options:")
    print("  --pack=NAME    Seed specific pack (treasury, wealth). Default: all packs")
    print("  --basic        Seed basic signals only (default)")
    print("  --scenarios    Seed from scenarios.json (realistic demo data)")
    print("  --all          Seed both basic signals and all scenarios")
    print("  --scenario=ID  Seed specific scenario by ID")
    print("  --evaluate     Trigger evaluations after seeding (default)")
    print("  --no-evaluate  Skip evaluation triggering")
    print()
    print("Available packs and scenarios:")
    for pack_name, config in PACK_CONFIGS.items():
        print(f"\n  {pack_name.upper()}:")
        scenarios_path = config["scenarios_path"]
        if scenarios_path.exists():
            with open(scenarios_path) as f:
                data = json.load(f)
            for s in data.get("scenarios", []):
                print(f"    {s['id']}: {s['name']}")


def main():
    """Main seed function."""
    print("=" * 60)
    print("Governance OS - Pack Seed Script")
    print("=" * 60)
    print()

    # Parse command line arguments
    args = sys.argv[1:]

    use_basic = True
    use_scenarios = False
    specific_scenarios = []
    target_pack = None  # None means all packs
    run_evaluate = True  # Default: trigger evaluations after seeding

    if "--help" in args or "-h" in args:
        print_usage()
        return

    for arg in args:
        if arg.startswith("--pack="):
            target_pack = arg.split("=", 1)[1]
        elif arg == "--scenarios":
            use_basic = False
            use_scenarios = True
        elif arg == "--all":
            use_basic = True
            use_scenarios = True
        elif arg.startswith("--scenario="):
            specific_scenarios.append(arg.split("=", 1)[1])
            use_basic = False
        elif arg == "--no-evaluate":
            run_evaluate = False
        elif arg == "--evaluate":
            run_evaluate = True

    # Create database session
    db = SessionLocal()

    try:
        # Always seed policies first (for specified pack or all packs)
        seed_policies(db, pack=target_pack)

        # Seed signals based on options
        if use_basic:
            seed_signals(db, pack=target_pack)

        if use_scenarios:
            seed_scenarios(db, pack=target_pack)
        elif specific_scenarios:
            seed_scenarios(db, pack=target_pack, scenario_ids=specific_scenarios)

        # Trigger evaluations to generate exceptions
        if run_evaluate:
            trigger_evaluations(db, pack=target_pack)

        print("=" * 60)
        print("Seeding completed successfully!")
        print()
        if run_evaluate:
            print("Exceptions have been generated. View them at:")
            print("  http://localhost:3000/exceptions")
        else:
            print("Next steps:")
            print("  1. Trigger evaluation: POST /api/v1/evaluations")
            print("  2. View exceptions: GET /api/v1/exceptions")
            print("  3. Record decisions: POST /api/v1/decisions")
        print()
        print("Or run the full demo: make demo-kernel")
        print("=" * 60)

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
