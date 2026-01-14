"""
Seed script for loading Treasury pack fixtures.

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
from packs.treasury.policy_templates import TREASURY_POLICY_TEMPLATES
from packs.treasury.signal_types import TREASURY_SIGNAL_TYPES

# Path to scenarios file
SCENARIOS_PATH = Path(__file__).parents[2] / "packs" / "treasury" / "fixtures" / "scenarios.json"


def seed_policies(db: Session):
    """Seed treasury policies."""
    print("Seeding treasury policies...")

    for key, template in TREASURY_POLICY_TEMPLATES.items():
        # Check if policy exists
        existing = db.query(Policy).filter(
            Policy.name == template["name"],
            Policy.pack == "treasury"
        ).first()

        if existing:
            print(f"  Policy '{template['name']}' already exists, skipping")
            continue

        # Create policy
        policy = Policy(
            name=template["name"],
            pack="treasury",
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
            valid_from=datetime.now(timezone.utc) - timedelta(days=30),  # Active for past 30 days
            valid_to=None,  # Currently active
            changelog="Initial version",
            created_by="system_seed"
        )
        db.add(policy_version)

        print(f"  Created policy: {template['name']}")

    db.commit()
    print("Policies seeded successfully\n")


def seed_signals(db: Session):
    """Seed sample treasury signals (basic set)."""
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
    print(f"  Created 4 sample signals")
    print("Signals seeded successfully\n")


def seed_scenarios(db: Session, scenario_ids: list[str] = None):
    """
    Seed signals from scenario definitions.

    Args:
        db: Database session
        scenario_ids: List of scenario IDs to load. If None, loads all scenarios.
    """
    if not SCENARIOS_PATH.exists():
        print(f"Scenarios file not found: {SCENARIOS_PATH}")
        return

    print("Loading scenarios from fixtures...")

    with open(SCENARIOS_PATH) as f:
        data = json.load(f)

    scenarios = data.get("scenarios", [])

    if scenario_ids:
        scenarios = [s for s in scenarios if s["id"] in scenario_ids]

    if not scenarios:
        print("  No matching scenarios found")
        return

    reliability_map = {
        "high": SignalReliability.HIGH,
        "medium": SignalReliability.MEDIUM,
        "low": SignalReliability.LOW
    }

    created_count = 0
    for scenario in scenarios:
        print(f"\n  Scenario: {scenario['name']}")
        print(f"    {scenario['narrative'][:100]}...")

        for signal_def in scenario.get("signals", []):
            signal = Signal(
                pack="treasury",
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
    print(f"\n  Created {created_count} signals from {len(scenarios)} scenarios")
    print("Scenarios seeded successfully\n")


def print_usage():
    """Print usage instructions."""
    print("Usage: python -m core.scripts.seed_fixtures [OPTIONS]")
    print()
    print("Options:")
    print("  --basic       Seed basic signals only (default)")
    print("  --scenarios   Seed from scenarios.json (realistic demo data)")
    print("  --all         Seed both basic signals and all scenarios")
    print("  --scenario=ID Seed specific scenario by ID")
    print()
    print("Available scenario IDs:")
    if SCENARIOS_PATH.exists():
        with open(SCENARIOS_PATH) as f:
            data = json.load(f)
        for s in data.get("scenarios", []):
            print(f"  {s['id']}: {s['name']}")


def main():
    """Main seed function."""
    print("=" * 60)
    print("Governance OS - Treasury Pack Seed Script")
    print("=" * 60)
    print()

    # Parse command line arguments
    args = sys.argv[1:]

    use_basic = True
    use_scenarios = False
    specific_scenarios = []

    if "--help" in args or "-h" in args:
        print_usage()
        return

    if "--scenarios" in args:
        use_basic = False
        use_scenarios = True
    elif "--all" in args:
        use_basic = True
        use_scenarios = True
    else:
        for arg in args:
            if arg.startswith("--scenario="):
                specific_scenarios.append(arg.split("=", 1)[1])
                use_basic = False

    # Create database session
    db = SessionLocal()

    try:
        # Always seed policies first
        seed_policies(db)

        # Seed signals based on options
        if use_basic:
            seed_signals(db)

        if use_scenarios:
            seed_scenarios(db)
        elif specific_scenarios:
            seed_scenarios(db, specific_scenarios)

        print("=" * 60)
        print("Seeding completed successfully!")
        print()
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
