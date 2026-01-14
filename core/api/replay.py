"""
Replay API Router.

Handles policy tuning workflow:
- Replay signals with draft or active policy versions
- Compare results between versions
- What-if analysis without production impact
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
import hashlib
import json

from core.database import get_db
from core.models import Policy, PolicyVersion, PolicyStatus, Signal, Evaluation, Exception as DBException
from core.services import Evaluator, ExceptionEngine
from core.schemas.policy import (
    ReplayRequest,
    ReplayResultSummary,
    ComparisonRequest,
    ComparisonResultSummary,
)
from core.api.dependencies import validate_pack

router = APIRouter(prefix="/replay", tags=["replay"])

# In-memory storage for replay results (in production, would be Redis or DB)
_replay_cache: Dict[str, Dict[str, Any]] = {}


@router.post("", response_model=ReplayResultSummary, status_code=201)
def run_replay(
    request: ReplayRequest,
    db: Session = Depends(get_db)
):
    """
    Run a replay evaluation against historical signals.

    This runs policy evaluation in isolation without affecting production data.
    Useful for testing draft policies before publishing.

    Workflow:
    1. Select signals (by date range or IDs)
    2. Evaluate using specified policy version (or active version)
    3. Count exceptions that would be raised
    4. Return summary for comparison
    """
    validate_pack(request.pack)

    # Get policy version to evaluate
    policy_version = None
    policy = None

    if request.policy_version_id:
        policy_version = db.query(PolicyVersion).filter(
            PolicyVersion.id == request.policy_version_id
        ).first()
        if not policy_version:
            raise HTTPException(status_code=404, detail="Policy version not found")
        policy = db.query(Policy).filter(Policy.id == policy_version.policy_id).first()
    else:
        # Find any active policy for this pack (for demo purposes)
        policy = db.query(Policy).filter(Policy.pack == request.pack).first()
        if not policy:
            raise HTTPException(status_code=404, detail=f"No policies found for pack: {request.pack}")

        now = datetime.now(timezone.utc)
        policy_version = db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy.id,
            PolicyVersion.status == PolicyStatus.ACTIVE,
            PolicyVersion.valid_from <= now,
        ).first()

        if not policy_version:
            raise HTTPException(status_code=404, detail="No active policy version found")

    # Select signals
    signal_query = db.query(Signal).filter(Signal.pack == request.pack)

    if request.signal_ids:
        signal_query = signal_query.filter(Signal.id.in_(request.signal_ids))
    else:
        # Default: signals from last 24 hours
        from_date = request.from_date or (datetime.now(timezone.utc) - timedelta(hours=24))
        to_date = request.to_date or datetime.now(timezone.utc)
        signal_query = signal_query.filter(
            Signal.observed_at >= from_date,
            Signal.observed_at <= to_date
        )

    signals = signal_query.order_by(Signal.observed_at.desc()).limit(100).all()

    if not signals:
        raise HTTPException(status_code=400, detail="No signals found for the specified criteria")

    # Run evaluation
    evaluator = Evaluator(db)
    exception_engine = ExceptionEngine(db)

    pass_count = 0
    fail_count = 0
    inconclusive_count = 0
    exceptions_raised = []
    evaluations = []

    for signal in signals:
        # Evaluate this signal against the policy
        evaluation = evaluator.evaluate(policy_version, [signal])

        if evaluation.result.value == "pass":
            pass_count += 1
        elif evaluation.result.value == "fail":
            fail_count += 1
            # Check if this would raise an exception
            exception = exception_engine.generate_exception(evaluation, policy_version)
            if exception:
                exceptions_raised.append({
                    "title": exception.title,
                    "severity": exception.severity.value,
                    "fingerprint": exception.fingerprint
                })
        else:
            inconclusive_count += 1

        evaluations.append({
            "signal_id": str(signal.id),
            "result": evaluation.result.value,
            "input_hash": evaluation.input_hash
        })

    # Generate replay ID
    replay_id = str(uuid4())

    # Cache result for comparison
    _replay_cache[replay_id] = {
        "replay_id": replay_id,
        "policy_version_id": str(policy_version.id),
        "policy_name": policy.name,
        "version_number": policy_version.version_number,
        "is_draft": policy_version.status == PolicyStatus.DRAFT,
        "signals_processed": len(signals),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "inconclusive_count": inconclusive_count,
        "exceptions_raised": exceptions_raised,
        "evaluations": evaluations,
        "executed_at": datetime.now(timezone.utc)
    }

    return ReplayResultSummary(
        replay_id=replay_id,
        policy_version_id=policy_version.id,
        policy_name=policy.name,
        version_number=policy_version.version_number,
        is_draft=policy_version.status == PolicyStatus.DRAFT,
        signals_processed=len(signals),
        pass_count=pass_count,
        fail_count=fail_count,
        inconclusive_count=inconclusive_count,
        exceptions_raised=len(exceptions_raised),
        executed_at=datetime.now(timezone.utc)
    )


@router.get("/{replay_id}")
def get_replay_result(
    replay_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed replay result by ID.
    """
    if replay_id not in _replay_cache:
        raise HTTPException(status_code=404, detail="Replay result not found or expired")

    return _replay_cache[replay_id]


@router.post("/compare", response_model=ComparisonResultSummary)
def compare_replays(
    request: ComparisonRequest,
    db: Session = Depends(get_db)
):
    """
    Compare two replay results.

    Typically used to compare:
    - Active version vs Draft version
    - Before policy change vs After policy change

    Returns counts of exceptions before/after and net change.
    """
    baseline = _replay_cache.get(request.baseline_replay_id)
    comparison = _replay_cache.get(request.comparison_replay_id)

    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline replay not found or expired")
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison replay not found or expired")

    # Compare exception fingerprints
    baseline_fingerprints = {e["fingerprint"] for e in baseline["exceptions_raised"]}
    comparison_fingerprints = {e["fingerprint"] for e in comparison["exceptions_raised"]}

    new_exceptions = len(comparison_fingerprints - baseline_fingerprints)
    resolved_exceptions = len(baseline_fingerprints - comparison_fingerprints)

    # Compare evaluations by signal
    baseline_evals = {e["signal_id"]: e for e in baseline["evaluations"]}
    comparison_evals = {e["signal_id"]: e for e in comparison["evaluations"]}

    all_signals = set(baseline_evals.keys()) | set(comparison_evals.keys())
    matching = 0
    divergent = 0

    for signal_id in all_signals:
        b_eval = baseline_evals.get(signal_id)
        c_eval = comparison_evals.get(signal_id)
        if b_eval and c_eval:
            if b_eval["result"] == c_eval["result"]:
                matching += 1
            else:
                divergent += 1

    # Generate summary message
    exception_delta = len(comparison["exceptions_raised"]) - len(baseline["exceptions_raised"])
    if exception_delta > 0:
        summary = f"Draft version would raise {exception_delta} MORE exceptions"
    elif exception_delta < 0:
        summary = f"Draft version would raise {abs(exception_delta)} FEWER exceptions"
    else:
        summary = "No change in exception count"

    if new_exceptions > 0 or resolved_exceptions > 0:
        summary += f" ({new_exceptions} new, {resolved_exceptions} resolved)"

    return ComparisonResultSummary(
        baseline_replay_id=request.baseline_replay_id,
        comparison_replay_id=request.comparison_replay_id,
        baseline_version_number=baseline["version_number"],
        comparison_version_number=comparison["version_number"],
        baseline_exceptions=len(baseline["exceptions_raised"]),
        comparison_exceptions=len(comparison["exceptions_raised"]),
        new_exceptions=new_exceptions,
        resolved_exceptions=resolved_exceptions,
        exception_delta=exception_delta,
        total_evaluations=len(all_signals),
        matching_evaluations=matching,
        divergent_evaluations=divergent,
        summary=summary
    )


@router.get("/cache/list")
def list_cached_replays():
    """
    List all cached replay results.

    Useful for finding replay IDs to compare.
    """
    return [
        {
            "replay_id": r["replay_id"],
            "policy_name": r["policy_name"],
            "version_number": r["version_number"],
            "is_draft": r["is_draft"],
            "exceptions_raised": len(r["exceptions_raised"]),
            "executed_at": r["executed_at"].isoformat() if isinstance(r["executed_at"], datetime) else r["executed_at"]
        }
        for r in _replay_cache.values()
    ]


@router.delete("/cache/{replay_id}", status_code=204)
def clear_replay_cache(replay_id: str):
    """
    Clear a specific replay result from cache.
    """
    if replay_id in _replay_cache:
        del _replay_cache[replay_id]


@router.delete("/cache", status_code=204)
def clear_all_cache():
    """
    Clear all replay results from cache.
    """
    _replay_cache.clear()
