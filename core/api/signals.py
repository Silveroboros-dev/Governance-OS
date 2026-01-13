"""
Signals API Router.

Handles signal ingestion.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.models import Signal, SignalReliability, AuditEvent, AuditEventType
from core.schemas.signal import SignalCreate, SignalResponse

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("", response_model=SignalResponse, status_code=201)
def create_signal(
    signal_data: SignalCreate,
    db: Session = Depends(get_db)
):
    """
    Ingest a new signal.

    Signals are timestamped facts with provenance.
    """
    # Map reliability string to enum
    reliability_map = {
        "high": SignalReliability.HIGH,
        "medium": SignalReliability.MEDIUM,
        "low": SignalReliability.LOW,
        "unverified": SignalReliability.UNVERIFIED
    }

    reliability = reliability_map.get(signal_data.reliability.lower())
    if not reliability:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reliability: {signal_data.reliability}"
        )

    # Create signal
    signal = Signal(
        pack=signal_data.pack,
        signal_type=signal_data.signal_type,
        payload=signal_data.payload,
        source=signal_data.source,
        reliability=reliability,
        observed_at=signal_data.observed_at,
        signal_metadata=signal_data.metadata
    )

    db.add(signal)
    db.flush()

    # Create audit event
    audit_event = AuditEvent(
        event_type=AuditEventType.SIGNAL_INGESTED,
        aggregate_type="signal",
        aggregate_id=signal.id,
        event_data={
            "signal_type": signal_data.signal_type,
            "source": signal_data.source,
            "pack": signal_data.pack
        },
        actor=signal_data.source
    )

    db.add(audit_event)
    db.commit()
    db.refresh(signal)

    return signal


@router.get("", response_model=List[SignalResponse])
def list_signals(
    pack: str = None,
    signal_type: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List signals with optional filtering.
    """
    query = db.query(Signal)

    if pack:
        query = query.filter(Signal.pack == pack)

    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)

    signals = query.order_by(Signal.ingested_at.desc()).limit(limit).all()

    return signals
