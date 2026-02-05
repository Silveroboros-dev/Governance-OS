"""
Intake Processing API Router.

Sprint 3: REST endpoint for document intake via IntakeAgent.

All extracted signals go to the approval queue for human review.
This endpoint does NOT create signals directly - it creates pending approvals.
"""

import time
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import AgentTrace, AgentType, AgentTraceStatus, ApprovalQueue, ApprovalActionType
from core.schemas.intake import (
    IntakeProcessRequest,
    IntakeProcessResponse,
    ExtractedSignalResponse,
    SourceSpanResponse,
    CanonicalizationMetrics,
)
from core.domain.canonicalizer import canonicalize, CanonicalStatus

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("/process", response_model=IntakeProcessResponse)
def process_document(
    request: IntakeProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process a document through the intake agent to extract signals.

    All extracted signals go to the approval queue for human review.
    This endpoint does NOT create signals directly.

    The flow is:
    1. Create AgentTrace for observability
    2. Run IntakeAgent extraction
    3. Create ApprovalQueue entries for each candidate
    4. Return results with trace_id and approval_ids

    Safety invariants:
    - All extractions require human approval before becoming signals
    - Full provenance via source spans
    - Complete audit trail via AgentTrace
    """
    start_time = time.time()
    submission_time = datetime.utcnow()
    session_id = uuid4()
    pack = request.pack.value
    document_source = request.document_source or "user_submission"
    # Use document_date if provided, otherwise fall back to submission time
    observed_at = (request.document_date or submission_time).isoformat()
    warnings = []

    # Create agent trace for observability
    trace = AgentTrace(
        agent_type=AgentType.INTAKE,
        session_id=session_id,
        pack=pack,
        document_source=document_source,
        input_summary={
            "document_length": len(request.document_text),
            "pack": pack,
            "source": document_source,
        }
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)

    try:
        # Import and run intake agent
        from coprocessor.agents.intake_agent import IntakeAgent

        agent = IntakeAgent()

        # Record tool call start
        extraction_start = time.time()

        # Run extraction (synchronous version)
        result = agent.extract_signals_sync(
            content=request.document_text,
            pack=pack,
            document_source=document_source,
            document_metadata={"submitted_via": "web_ui"},
            trace_id=str(trace.id),
        )

        extraction_duration_ms = int((time.time() - extraction_start) * 1000)

        # Record extraction tool call in trace
        trace.add_tool_call(
            tool="extract_signals",
            args={
                "pack": pack,
                "document_source": document_source,
                "content_length": len(request.document_text),
            },
            result={
                "total_candidates": result.total_candidates,
                "high_confidence": result.high_confidence_count,
                "requires_verification": result.requires_verification_count,
            },
            duration_ms=extraction_duration_ms,
        )

        # Run Canonicalizer on extraction results
        # This is a pure function: same candidates -> same canonical signals
        candidate_dicts = [
            {
                "id": getattr(candidate, "id", f"C{i}"),
                "signal_type": candidate.signal_type,
                "payload": candidate.payload,
                "confidence": candidate.confidence,
                "source_spans": [
                    {
                        "start_char": span.start_char,
                        "end_char": span.end_char,
                        "text": span.text,
                        "page": span.page,
                    }
                    for span in candidate.source_spans
                ],
            }
            for i, candidate in enumerate(result.candidates)
        ]

        canon_result = canonicalize(candidate_dicts, pack)

        # Record canonicalization in trace
        trace.add_tool_call(
            tool="canonicalize",
            args={"candidate_count": len(candidate_dicts), "pack": pack},
            result={
                "breach_count": canon_result.breach_count,
                "observation_count": canon_result.observation_count,
                "dropped_count": canon_result.dropped_count,
                "merged_count": canon_result.merged_count,
                "downgrade_count": canon_result.downgrade_count,
            },
            duration_ms=0,
        )

        canon_metrics = CanonicalizationMetrics(
            enabled=True,
            breach_count=canon_result.breach_count,
            observation_count=canon_result.observation_count,
            dropped_count=canon_result.dropped_count,
            merged_count=canon_result.merged_count,
            downgrade_count=canon_result.downgrade_count,
            lookthrough_blocked_count=canon_result.lookthrough_blocked_count,
        )

        # Create approval queue entries — only for breach + observation signals
        # (dropped and merged signals do not go to approval queue)
        approval_ids = []
        signals_response = []

        # Build lookup by candidate ID for O(1) matching
        candidate_by_id = {}
        for i, candidate in enumerate(result.candidates):
            cid = getattr(candidate, "id", f"C{i}")
            candidate_by_id[cid] = candidate

        for canon_signal in canon_result.signals:
            if canon_signal.canonical_status in (CanonicalStatus.DROPPED, CanonicalStatus.MERGED):
                continue

            # Find matching original candidate by source_candidate_id
            original_candidate = candidate_by_id.get(canon_signal.source_candidate_id)

            # Build approval payload with canonicalization metadata
            approval_payload = {
                "pack": pack,
                "signal_type": canon_signal.signal_type,
                "payload": canon_signal.payload,
                "source": document_source,
                "observed_at": observed_at,
                "source_spans": [
                    {
                        "start_char": span.start_char,
                        "end_char": span.end_char,
                        "text": span.text,
                        "page": span.page,
                    }
                    for span in (original_candidate.source_spans if original_candidate else [])
                ],
                "extraction_notes": (original_candidate.extraction_notes if original_candidate else None),
                # Canonicalization metadata
                "canonical_status": canon_signal.canonical_status.value,
                "canonical_severity": canon_signal.severity,
                "canonical_flags": [f.value for f in canon_signal.flags],
                "completeness_score": canon_signal.completeness_score,
                "missing_fields": canon_signal.missing_fields,
                "constraint_id": canon_signal.constraint_id,
                "dedupe_key": canon_signal.dedupe_key,
            }

            # Use deterministic title from Canonicalizer
            signal_title = canon_signal.title

            # Create approval queue entry
            approval = ApprovalQueue(
                action_type=ApprovalActionType.SIGNAL,
                payload=approval_payload,
                proposed_by="intake_agent",
                confidence=canon_signal.confidence,
                trace_id=trace.id,
                summary=signal_title,
            )
            db.add(approval)
            db.flush()  # Get ID without committing
            approval_ids.append(str(approval.id))

            # Build response signal
            source_spans = []
            if original_candidate:
                source_spans = [
                    SourceSpanResponse(
                        start_char=span.start_char,
                        end_char=span.end_char,
                        text=span.text,
                        page=span.page,
                    )
                    for span in original_candidate.source_spans
                ]

            signals_response.append(ExtractedSignalResponse(
                signal_type=canon_signal.signal_type,
                payload=canon_signal.payload,
                confidence=canon_signal.confidence,
                source_spans=source_spans,
                extraction_notes=(original_candidate.extraction_notes if original_candidate else None),
                requires_verification=canon_signal.confidence < 0.7,
            ))

        # Record approval creation tool call
        trace.add_tool_call(
            tool="create_approvals",
            args={"candidate_count": len(result.candidates)},
            result={"approval_ids": approval_ids},
            duration_ms=0,
        )

        # Mark trace as completed
        processing_time_ms = int((time.time() - start_time) * 1000)
        trace.complete(output_summary={
            "total_candidates": result.total_candidates,
            "high_confidence": result.high_confidence_count,
            "requires_verification": result.requires_verification_count,
            "approval_ids": approval_ids,
            "processing_time_ms": processing_time_ms,
        })

        # Add extraction notes as warnings if present
        if result.extraction_notes:
            warnings.append(result.extraction_notes)

        db.commit()

        return IntakeProcessResponse(
            trace_id=str(trace.id),
            signals=signals_response,
            approval_ids=approval_ids,
            total_candidates=result.total_candidates,
            high_confidence=result.high_confidence_count,
            requires_verification=result.requires_verification_count,
            processing_time_ms=processing_time_ms,
            extraction_notes=result.extraction_notes,
            warnings=warnings,
            canonicalization=canon_metrics,
        )

    except ImportError as e:
        # IntakeAgent not available (missing anthropic package or API key)
        trace.fail(f"IntakeAgent not available: {str(e)}")
        db.commit()
        raise HTTPException(
            status_code=503,
            detail=f"Intake agent not available. Ensure anthropic package is installed and ANTHROPIC_API_KEY is set. Error: {str(e)}"
        )

    except ValueError as e:
        # Invalid input (bad pack, etc.)
        trace.fail(f"Invalid input: {str(e)}")
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Unexpected error
        trace.fail(f"Processing failed: {str(e)}")
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )
