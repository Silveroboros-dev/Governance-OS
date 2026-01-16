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
)

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
    session_id = uuid4()
    pack = request.pack.value
    document_source = request.document_source or "user_submission"
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

        # Create approval queue entries for each candidate
        approval_ids = []
        signals_response = []

        for candidate in result.candidates:
            # Build approval payload
            approval_payload = {
                "pack": pack,
                "signal_type": candidate.signal_type,
                "payload": candidate.payload,
                "source": document_source,
                "observed_at": datetime.utcnow().isoformat(),
                "source_spans": [
                    {
                        "start_char": span.start_char,
                        "end_char": span.end_char,
                        "text": span.text,
                        "page": span.page,
                    }
                    for span in candidate.source_spans
                ],
                "extraction_notes": candidate.extraction_notes,
            }

            # Create approval queue entry
            approval = ApprovalQueue(
                action_type=ApprovalActionType.SIGNAL,
                payload=approval_payload,
                proposed_by="intake_agent",
                confidence=candidate.confidence,
                trace_id=trace.id,
                summary=f"Extract {candidate.signal_type.replace('_', ' ')} from {document_source}",
            )
            db.add(approval)
            db.flush()  # Get ID without committing
            approval_ids.append(str(approval.id))

            # Build response signal
            signals_response.append(ExtractedSignalResponse(
                signal_type=candidate.signal_type,
                payload=candidate.payload,
                confidence=candidate.confidence,
                source_spans=[
                    SourceSpanResponse(
                        start_char=span.start_char,
                        end_char=span.end_char,
                        text=span.text,
                        page=span.page,
                    )
                    for span in candidate.source_spans
                ],
                extraction_notes=candidate.extraction_notes,
                requires_verification=candidate.requires_verification,
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
