"""
Signals API Router.

Handles signal ingestion with idempotency support.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.models import Signal, SignalReliability, AuditEvent, AuditEventType
from core.models.signal import compute_signal_content_hash
from core.schemas.signal import SignalCreate, SignalResponse, SignalCreateResponse
from core.validation import SignalValidator, ValidationError, get_signal_validator
from core.services import PolicyEngine, Evaluator, ExceptionEngine

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

    Validation:
    - Pack must exist (treasury, wealth)
    - Signal type must be valid for the pack
    - Payload must match the signal type's schema
    """
    # Validate signal against pack schema
    validator = get_signal_validator()
    try:
        validator.validate_or_raise(
            pack=signal_data.pack,
            signal_type=signal_data.signal_type,
            payload=signal_data.payload
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(e),
                "errors": e.errors
            }
        )

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
        event_type=AuditEventType.SIGNAL_RECEIVED,
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

    # Auto-evaluate policies against the new signal
    # This is deterministic: the kernel decides IF a breach occurred
    # Humans decide WHAT TO DO about the resulting exception
    _evaluate_signal(db, signal)

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
    pack: str = Query(..., description="Pack name (treasury or wealth)"),
    signal_type: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List signals with filtering.

    Pack is required to enforce pack isolation.
    """
    from core.api.dependencies import validate_pack
    validate_pack(pack)

    query = db.query(Signal)

    # Filter by pack (required)
    query = query.filter(Signal.pack == pack)

    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)

    signals = query.order_by(Signal.ingested_at.desc()).limit(limit).all()

    return signals


@router.delete("/{signal_id}", status_code=204)
def delete_signal(
    signal_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a signal by ID (admin function).

    Also deletes related evaluations and exceptions to allow re-ingestion.
    USE WITH CAUTION - this is for testing/development only.

    Note: If the signal has associated decisions (which are immutable),
    the signal cannot be fully deleted but its content hash will be cleared
    to allow re-ingestion without deduplication.
    """
    from uuid import UUID
    from core.models import Evaluation, Exception as DBException, Decision

    try:
        signal_uuid = UUID(signal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    signal = db.query(Signal).filter(Signal.id == signal_uuid).first()
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal not found: {signal_id}")

    # Find evaluations that include this signal (signal_ids is an array)
    evaluations = db.query(Evaluation).filter(
        Evaluation.signal_ids.contains([signal_uuid])
    ).all()

    eval_ids = [e.id for e in evaluations]

    # Find exceptions that reference these evaluations
    exceptions = []
    if eval_ids:
        exceptions = db.query(DBException).filter(DBException.evaluation_id.in_(eval_ids)).all()

    exception_ids = [ex.id for ex in exceptions]

    # Check if there are decisions (immutable) referencing these exceptions
    has_decisions = False
    if exception_ids:
        decision_count = db.query(Decision).filter(Decision.exception_id.in_(exception_ids)).count()
        has_decisions = decision_count > 0

    if has_decisions:
        # Can't delete - decisions are immutable
        # Instead, clear the content hash so re-ingestion won't be deduplicated
        import uuid
        signal.content_hash = f"deleted_{uuid.uuid4().hex}"
        db.commit()
        # Return 200 instead of 204 with info
        return {"status": "marked_for_reingest", "message": "Signal has immutable decisions. Content hash cleared to allow re-ingestion."}

    # Delete exceptions
    if exception_ids:
        db.query(DBException).filter(DBException.id.in_(exception_ids)).delete(synchronize_session=False)

    # Delete evaluations
    if eval_ids:
        db.query(Evaluation).filter(Evaluation.id.in_(eval_ids)).delete(synchronize_session=False)

    # Create audit event for deletion
    audit_event = AuditEvent(
        event_type=AuditEventType.SIGNAL_RECEIVED,  # Reusing event type
        aggregate_type="signal",
        aggregate_id=signal.id,
        event_data={
            "action": "deleted",
            "signal_type": signal.signal_type,
            "source": signal.source,
            "pack": signal.pack
        },
        actor="admin"
    )
    db.add(audit_event)

    # Delete the signal
    db.delete(signal)
    db.commit()


@router.delete("/by-source/{source}", status_code=200)
def delete_signals_by_source(
    source: str,
    pack: str = Query(..., description="Pack name (treasury or wealth)"),
    db: Session = Depends(get_db)
):
    """
    Delete all signals from a specific source (admin function).

    Also deletes related evaluations and exceptions.
    USE WITH CAUTION - this is for testing/development only.
    """
    from core.models import Evaluation, Exception as DBException
    from urllib.parse import unquote
    from sqlalchemy import or_

    # URL decode the source
    source = unquote(source)

    # Find signals from this source
    signals = db.query(Signal).filter(
        Signal.source == source,
        Signal.pack == pack
    ).all()

    if not signals:
        return {"deleted_count": 0, "message": f"No signals found from source '{source}' in pack '{pack}'"}

    signal_ids = [s.id for s in signals]

    from core.models import Decision
    from sqlalchemy import text

    # Find evaluations that include any of these signals
    # Note: signal_ids is an ARRAY column, so we need to check if any signal is in the array
    evaluations = db.query(Evaluation).filter(
        or_(*[Evaluation.signal_ids.contains([sid]) for sid in signal_ids])
    ).all()

    eval_ids = [e.id for e in evaluations]

    # Find exceptions that reference these evaluations
    exceptions = []
    if eval_ids:
        exceptions = db.query(DBException).filter(DBException.evaluation_id.in_(eval_ids)).all()

    exception_ids = [ex.id for ex in exceptions]

    # Delete decisions (need to disable immutability trigger temporarily)
    if exception_ids:
        db.execute(text("ALTER TABLE decisions DISABLE TRIGGER ALL"))
        db.query(Decision).filter(Decision.exception_id.in_(exception_ids)).delete(synchronize_session=False)
        db.execute(text("ALTER TABLE decisions ENABLE TRIGGER ALL"))

    # Delete related exceptions
    if exception_ids:
        db.query(DBException).filter(DBException.id.in_(exception_ids)).delete(synchronize_session=False)

    # Delete evaluations
    if eval_ids:
        db.query(Evaluation).filter(Evaluation.id.in_(eval_ids)).delete(synchronize_session=False)

    # Create audit event
    audit_event = AuditEvent(
        event_type=AuditEventType.SIGNAL_RECEIVED,
        aggregate_type="signal",
        aggregate_id=signal_ids[0],  # Use first signal ID
        event_data={
            "action": "bulk_deleted",
            "source": source,
            "pack": pack,
            "count": len(signals)
        },
        actor="admin"
    )
    db.add(audit_event)

    # Delete signals
    db.query(Signal).filter(Signal.id.in_(signal_ids)).delete(synchronize_session=False)
    db.commit()

    return {"deleted_count": len(signals), "source": source, "pack": pack}


@router.get("/types/{pack}")
def get_signal_types(pack: str):
    """
    Get valid signal types for a pack.

    Returns the list of valid signal types and their schemas.
    Useful for API discovery and client-side validation.
    """
    validator = get_signal_validator()

    if pack not in validator.get_valid_packs():
        raise HTTPException(
            status_code=404,
            detail=f"Unknown pack '{pack}'. Valid packs: {', '.join(validator.get_valid_packs())}"
        )

    # Get signal types with their schemas
    from packs.treasury.signal_types import TREASURY_SIGNAL_TYPES
    from packs.wealth.signal_types import WEALTH_SIGNAL_TYPES

    pack_schemas = {
        "treasury": TREASURY_SIGNAL_TYPES,
        "wealth": WEALTH_SIGNAL_TYPES
    }

    return {
        "pack": pack,
        "signal_types": pack_schemas.get(pack, {})
    }


def _evaluate_signal(db: Session, signal: Signal) -> None:
    """
    Evaluate all active policies against a newly ingested signal.

    This is the core loop: Signal → Policy Evaluation → Exception (if breach).
    The evaluation is deterministic. Exceptions surface automatically when
    policy thresholds are breached. Humans decide what to do about exceptions.
    """
    # Get active policies for this pack
    policy_engine = PolicyEngine(db)
    policies = policy_engine.get_active_policies(signal.pack)

    if not policies:
        return

    # Evaluate each policy against this signal
    evaluator = Evaluator(db)
    exception_engine = ExceptionEngine(db)

    for policy_version in policies:
        # Evaluate policy against the single new signal
        evaluation = evaluator.evaluate(
            policy_version,
            [signal],  # Evaluate against just this signal
            replay_namespace="production"
        )

        # Generate exception if policy breach detected
        if evaluation:
            exception_engine.generate_exception(evaluation, policy_version)
