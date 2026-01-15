"""
Agent Traces API Router.

Sprint 3: Endpoints for agent execution observability.

Provides visibility into:
- What inputs agents received
- Which tools were called and their results
- What outputs were produced
- Any errors that occurred
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID

from core.database import get_db
from core.models import AgentTrace, AgentType, AgentTraceStatus, ApprovalQueue
from core.schemas.trace import (
    TraceCreate, TraceResponse, TraceDetailResponse,
    TraceListResponse, TraceToolCallsResponse,
    TraceCompleteRequest, TraceFailRequest, ToolCallSchema
)

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=TraceListResponse)
def list_traces(
    agent_type: Optional[str] = Query(None, description="Filter by agent type: intake, narrative, policy_draft"),
    status: Optional[str] = Query(None, description="Filter by status: running, completed, failed"),
    pack: Optional[str] = Query(None, description="Filter by pack: treasury, wealth"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List agent traces with filtering and pagination.

    Returns traces ordered by started_at descending (most recent first).
    """
    query = db.query(AgentTrace)

    # Apply filters
    if agent_type:
        try:
            agent_enum = AgentType(agent_type)
            query = query.filter(AgentTrace.agent_type == agent_enum)
        except ValueError:
            valid_types = ", ".join([t.value for t in AgentType])
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent_type: {agent_type}. Valid values: {valid_types}"
            )

    if status:
        try:
            status_enum = AgentTraceStatus(status)
            query = query.filter(AgentTrace.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: running, completed, failed"
            )

    if pack:
        query = query.filter(AgentTrace.pack == pack)

    # Get total count
    total = query.count()

    # Order by started_at descending
    query = query.order_by(AgentTrace.started_at.desc())

    # Paginate
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return TraceListResponse(
        items=[_trace_to_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{trace_id}", response_model=TraceDetailResponse)
def get_trace(
    trace_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific agent trace with full details including tool calls."""
    trace = db.query(AgentTrace).filter(AgentTrace.id == trace_id).first()

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")

    return _trace_to_detail_response(trace, db)


@router.get("/{trace_id}/tool-calls", response_model=TraceToolCallsResponse)
def get_trace_tool_calls(
    trace_id: UUID,
    db: Session = Depends(get_db)
):
    """Get just the tool calls for a trace."""
    trace = db.query(AgentTrace).filter(AgentTrace.id == trace_id).first()

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")

    tool_calls = []
    if trace.tool_calls:
        for call in trace.tool_calls:
            tool_calls.append(ToolCallSchema(
                tool=call.get("tool", ""),
                args=call.get("args", {}),
                result=call.get("result"),
                duration_ms=call.get("duration_ms", 0),
                timestamp=call.get("timestamp"),
                error=call.get("error")
            ))

    return TraceToolCallsResponse(
        trace_id=trace.id,
        tool_calls=tool_calls,
        total_calls=len(tool_calls)
    )


@router.post("", response_model=TraceResponse, status_code=201)
def create_trace(
    trace_data: TraceCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new agent trace.

    Called when an agent execution starts.
    """
    try:
        agent_type = AgentType(trace_data.agent_type)
    except ValueError:
        valid_types = ", ".join([t.value for t in AgentType])
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent_type: {trace_data.agent_type}. Valid values: {valid_types}"
        )

    trace = AgentTrace(
        agent_type=agent_type,
        session_id=trace_data.session_id,
        pack=trace_data.pack,
        document_source=trace_data.document_source,
        input_summary=trace_data.input_summary
    )

    db.add(trace)
    db.commit()
    db.refresh(trace)

    return _trace_to_response(trace)


@router.post("/{trace_id}/complete", response_model=TraceResponse)
def complete_trace(
    trace_id: UUID,
    request: TraceCompleteRequest,
    db: Session = Depends(get_db)
):
    """Mark a trace as completed successfully."""
    trace = db.query(AgentTrace).filter(AgentTrace.id == trace_id).first()

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")

    if trace.status != AgentTraceStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Trace already {trace.status.value}"
        )

    trace.complete(output_summary=request.output_summary)

    db.commit()
    db.refresh(trace)

    return _trace_to_response(trace)


@router.post("/{trace_id}/fail", response_model=TraceResponse)
def fail_trace(
    trace_id: UUID,
    request: TraceFailRequest,
    db: Session = Depends(get_db)
):
    """Mark a trace as failed."""
    trace = db.query(AgentTrace).filter(AgentTrace.id == trace_id).first()

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")

    if trace.status != AgentTraceStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Trace already {trace.status.value}"
        )

    trace.fail(error_message=request.error_message)

    db.commit()
    db.refresh(trace)

    return _trace_to_response(trace)


@router.post("/{trace_id}/tool-call", response_model=TraceResponse)
def add_tool_call(
    trace_id: UUID,
    tool_call: ToolCallSchema,
    db: Session = Depends(get_db)
):
    """Add a tool call to a trace."""
    trace = db.query(AgentTrace).filter(AgentTrace.id == trace_id).first()

    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")

    if trace.status != AgentTraceStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add tool calls to {trace.status.value} trace"
        )

    trace.add_tool_call(
        tool=tool_call.tool,
        args=tool_call.args,
        result=tool_call.result,
        duration_ms=tool_call.duration_ms,
        error=tool_call.error
    )

    db.commit()
    db.refresh(trace)

    return _trace_to_response(trace)


@router.get("/stats/summary")
def get_trace_stats(db: Session = Depends(get_db)):
    """Get summary statistics for agent traces."""
    running_count = db.query(AgentTrace).filter(
        AgentTrace.status == AgentTraceStatus.RUNNING
    ).count()

    completed_count = db.query(AgentTrace).filter(
        AgentTrace.status == AgentTraceStatus.COMPLETED
    ).count()

    failed_count = db.query(AgentTrace).filter(
        AgentTrace.status == AgentTraceStatus.FAILED
    ).count()

    # Count by agent type
    by_type = {}
    for agent_type in AgentType:
        count = db.query(AgentTrace).filter(
            AgentTrace.agent_type == agent_type
        ).count()
        by_type[agent_type.value] = count

    # Average duration for completed traces
    avg_duration = db.query(func.avg(AgentTrace.total_duration_ms)).filter(
        AgentTrace.status == AgentTraceStatus.COMPLETED
    ).scalar()

    return {
        "running": running_count,
        "completed": completed_count,
        "failed": failed_count,
        "by_agent_type": by_type,
        "average_duration_ms": int(avg_duration) if avg_duration else None
    }


# Helper functions

def _trace_to_response(trace: AgentTrace) -> TraceResponse:
    """Convert AgentTrace model to response schema."""
    return TraceResponse(
        id=trace.id,
        agent_type=trace.agent_type.value,
        session_id=trace.session_id,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
        status=trace.status.value,
        input_summary=trace.input_summary,
        output_summary=trace.output_summary,
        error_message=trace.error_message,
        total_duration_ms=trace.total_duration_ms,
        pack=trace.pack,
        document_source=trace.document_source
    )


def _trace_to_detail_response(trace: AgentTrace, db: Session) -> TraceDetailResponse:
    """Convert AgentTrace model to detailed response schema."""
    # Count approvals for this trace
    approval_count = db.query(ApprovalQueue).filter(
        ApprovalQueue.trace_id == trace.id
    ).count()

    # Convert tool calls
    tool_calls = None
    if trace.tool_calls:
        tool_calls = []
        for call in trace.tool_calls:
            tool_calls.append(ToolCallSchema(
                tool=call.get("tool", ""),
                args=call.get("args", {}),
                result=call.get("result"),
                duration_ms=call.get("duration_ms", 0),
                timestamp=call.get("timestamp"),
                error=call.get("error")
            ))

    return TraceDetailResponse(
        id=trace.id,
        agent_type=trace.agent_type.value,
        session_id=trace.session_id,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
        status=trace.status.value,
        input_summary=trace.input_summary,
        output_summary=trace.output_summary,
        error_message=trace.error_message,
        total_duration_ms=trace.total_duration_ms,
        pack=trace.pack,
        document_source=trace.document_source,
        tool_calls=tool_calls,
        approval_count=approval_count
    )
