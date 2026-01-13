"""
Seed script for loading Treasury pack fixtures.

Loads policies and sample signals for demonstration.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parents[2]))

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine, Base
from core.models import Policy, PolicyVersion, PolicyStatus, Signal, SignalReliability
from packs.treasury.policy_templates import TREASURY_POLICY_TEMPLATES
from packs.treasury.signal_types import TREASURY_SIGNAL_TYPES


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
            valid_from=datetime.utcnow() - timedelta(days=30),  # Active for past 30 days
            valid_to=None,  # Currently active
            changelog="Initial version",
            created_by="system_seed"
        )
        db.add(policy_version)

        print(f"  Created policy: {template['name']}")

    db.commit()
    print("Policies seeded successfully\n")


def seed_signals(db: Session):
    """Seed sample treasury signals."""
    print("Seeding treasury signals...")

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
        observed_at=datetime.utcnow() - timedelta(hours=2),
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
        observed_at=datetime.utcnow() - timedelta(hours=1),
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
        observed_at=datetime.utcnow() - timedelta(minutes=30),
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
        observed_at=datetime.utcnow() - timedelta(minutes=30),
        signal_metadata={"system": "risk_dashboard", "alert_id": "SOL_001"}
    )
    db.add(signal4)

    db.commit()
    print(f"  Created 4 sample signals")
    print("Signals seeded successfully\n")


def main():
    """Main seed function."""
    print("=" * 60)
    print("Governance OS - Treasury Pack Seed Script")
    print("=" * 60)
    print()

    # Create database session
    db = SessionLocal()

    try:
        # Seed data
        seed_policies(db)
        seed_signals(db)

        print("=" * 60)
        print("Seeding completed successfully!")
        print()
        print("Next steps:")
        print("  1. Trigger evaluation: POST /api/v1/evaluations")
        print("  2. View exceptions: GET /api/v1/exceptions")
        print("  3. Record decisions: POST /api/v1/decisions")
        print("=" * 60)

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
