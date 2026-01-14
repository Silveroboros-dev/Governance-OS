"""
Signals API Router.

Handles signal ingestion with idempotency support.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.models import Signal, SignalReliability, AuditEvent, AuditEventType
from core.models.signal import compute_signal_content_hash
from core.schemas.signal import SignalCreate, SignalResponse, SignalCreateResponse

router = APIRouter(prefix="/signals", tags=["signals"])


@router.post("", response_model=SignalCreateResponse, status_code=201)
def create_signal(
    signal_data: SignalCreate,
    db: Session = Depends(get_db)
):
    """
    Ingest a new signal (idempotent).

    Signals are timestamped facts with provenance.
    Duplicate signals (same content) return the existing signal.

    Idempotency is determined by:
    1. Client-provided idempotency_key (if given)
    2. Content hash (pack + signal_type + payload + source + observed_at)
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

    # Compute content hash for idempotency
    content_hash = signal_data.idempotency_key or compute_signal_content_hash(
        pack=signal_data.pack,
        signal_type=signal_data.signal_type,
        payload=signal_data.payload,
        source=signal_data.source,
        observed_at=signal_data.observed_at
    )

    # Check for existing signal with same content hash (idempotency check)
    existing_signal = db.query(Signal).filter(
        Signal.content_hash == content_hash
    ).first()

    if existing_signal:
        # Return existing signal (idempotent behavior)
        return SignalCreateResponse(
            id=existing_signal.id,
            pack=existing_signal.pack,
            signal_type=existing_signal.signal_type,
            payload=existing_signal.payload,
            source=existing_signal.source,
            reliability=existing_signal.reliability.value,
            observed_at=existing_signal.observed_at,
            ingested_at=existing_signal.ingested_at,
            metadata=existing_signal.signal_metadata,
            content_hash=existing_signal.content_hash,
            was_deduplicated=True
        )

    # Create new signal
    signal = Signal(
        pack=signal_data.pack,
        signal_type=signal_data.signal_type,
        payload=signal_data.payload,
        source=signal_data.source,
        reliability=reliability,
        observed_at=signal_data.observed_at,
        signal_metadata=signal_data.metadata,
        content_hash=content_hash
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
            "pack": signal_data.pack,
            "content_hash": content_hash
        },
        actor=signal_data.source
    )

    db.add(audit_event)
    db.commit()
    db.refresh(signal)

    return SignalCreateResponse(
        id=signal.id,
        pack=signal.pack,
        signal_type=signal.signal_type,
        payload=signal.payload,
        source=signal.source,
        reliability=signal.reliability.value,
        observed_at=signal.observed_at,
        ingested_at=signal.ingested_at,
        metadata=signal.signal_metadata,
        content_hash=signal.content_hash,
        was_deduplicated=False
    )


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
