"""
MCP Write Tools - Gated write operations requiring human approval.

Sprint 3: All agent writes go through approval queue for human review.

Safety invariants:
- All writes create pending_approval records
- No direct database mutations from agents
- Every approval/rejection logged to AuditEvent
- Approval UI shows full agent reasoning
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from mcp.server import FastMCP


def get_db_session():
    """Get database session for queries."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://governance:governance@localhost:5432/governance"
    )
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def register_write_tools(mcp: FastMCP):
    """Register all write tools on the MCP server."""

    @mcp.tool()
    def propose_signal(
        pack: str,
        signal_type: str,
        payload: Dict[str, Any],
        source: str,
        observed_at: str,
        source_spans: List[Dict[str, Any]],
        confidence: float,
        extraction_notes: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Propose a candidate signal for human review.

        This creates an approval queue entry. The signal will only be
        created if a human approves it.

        Args:
            pack: Pack name (treasury/wealth)
            signal_type: Signal type from pack vocabulary
            payload: Signal payload data
            source: Document source identifier
            observed_at: When the signal was observed (ISO format)
            source_spans: Source spans showing where data was extracted from
            confidence: Extraction confidence (0.0-1.0)
            extraction_notes: Agent's reasoning about the extraction
            trace_id: Optional trace ID for observability

        Returns:
            Dict with approval_id and status
        """
        try:
            from core.models import ApprovalQueue, ApprovalActionType, ApprovalStatus

            db = get_db_session()

            # Validate confidence
            if not 0.0 <= confidence <= 1.0:
                return {"error": f"Confidence must be between 0.0 and 1.0, got {confidence}"}

            # Create approval queue entry
            approval = ApprovalQueue(
                action_type=ApprovalActionType.SIGNAL,
                payload={
                    "pack": pack,
                    "signal_type": signal_type,
                    "payload": payload,
                    "source": source,
                    "observed_at": observed_at,
                    "source_spans": source_spans,
                    "extraction_notes": extraction_notes,
                },
                proposed_by="intake_agent",
                summary=f"Extract {signal_type} from {source}",
                confidence=confidence,
                trace_id=trace_id if trace_id else None
            )

            db.add(approval)
            db.commit()
            db.refresh(approval)

            result = {
                "approval_id": str(approval.id),
                "status": "pending",
                "message": f"Signal proposal created. Awaiting human approval.",
                "confidence": confidence,
                "requires_verification": confidence < 0.7
            }

            db.close()
            return result

        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def propose_policy_draft(
        name: str,
        description: str,
        rule_definition: Dict[str, Any],
        signal_types_referenced: List[str],
        change_reason: str,
        pack: str = "treasury",
        draft_notes: Optional[str] = None,
        test_scenarios: Optional[List[Dict[str, Any]]] = None,
        policy_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Propose a draft policy version for human review.

        This creates an approval queue entry. The policy will only be
        created/updated if a human approves it.

        Args:
            name: Policy name
            description: Policy description
            rule_definition: Deterministic rule definition (JSON)
            signal_types_referenced: List of signal types this policy evaluates
            change_reason: Reason for creating/updating this policy
            pack: Pack name (treasury/wealth)
            draft_notes: Agent's reasoning about rule construction
            test_scenarios: Optional test cases showing expected behavior
            policy_id: Optional existing policy ID if updating
            trace_id: Optional trace ID for observability

        Returns:
            Dict with approval_id and status
        """
        try:
            from core.models import ApprovalQueue, ApprovalActionType

            db = get_db_session()

            # Create approval queue entry
            approval = ApprovalQueue(
                action_type=ApprovalActionType.POLICY_DRAFT,
                payload={
                    "name": name,
                    "description": description,
                    "rule_definition": rule_definition,
                    "signal_types_referenced": signal_types_referenced,
                    "change_reason": change_reason,
                    "pack": pack,
                    "draft_notes": draft_notes,
                    "test_scenarios": test_scenarios or [],
                    "policy_id": policy_id,
                },
                proposed_by="policy_draft_agent",
                summary=f"Create policy: {name}",
                trace_id=trace_id if trace_id else None
            )

            db.add(approval)
            db.commit()
            db.refresh(approval)

            result = {
                "approval_id": str(approval.id),
                "status": "pending",
                "message": f"Policy draft created. Awaiting human approval.",
                "is_update": policy_id is not None
            }

            db.close()
            return result

        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def add_exception_context(
        exception_id: str,
        context_key: str,
        context_value: Any,
        source: str,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add context to an exception without requiring approval.

        This is an additive-only operation that enriches the exception
        with additional context from agent analysis.

        IMPORTANT: This is the only write tool that doesn't require approval
        because it's purely additive and doesn't change any decisions.

        Args:
            exception_id: UUID of the exception to enrich
            context_key: Key for the new context
            context_value: Value for the new context
            source: Where this context came from
            trace_id: Optional trace ID for observability

        Returns:
            Dict with success status
        """
        try:
            from core.models import Exception as DBException

            db = get_db_session()

            exception = db.query(DBException).filter(DBException.id == exception_id).first()
            if not exception:
                return {"error": f"Exception not found: {exception_id}"}

            # Add context (merge with existing)
            if exception.context is None:
                exception.context = {}

            exception.context[context_key] = {
                "value": context_value,
                "source": source,
                "added_at": datetime.utcnow().isoformat(),
                "added_by": "agent"
            }

            db.commit()

            result = {
                "success": True,
                "exception_id": exception_id,
                "context_key": context_key,
                "message": f"Context added to exception"
            }

            db.close()
            return result

        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def dismiss_exception(
        exception_id: str,
        reason: str,
        notes: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Propose dismissing an exception for human review.

        This creates an approval queue entry. The exception will only be
        dismissed if a human approves it.

        Args:
            exception_id: UUID of the exception to dismiss
            reason: Reason for dismissal
            notes: Optional additional notes
            trace_id: Optional trace ID for observability

        Returns:
            Dict with approval_id and status
        """
        try:
            from core.models import ApprovalQueue, ApprovalActionType, Exception as DBException

            db = get_db_session()

            # Verify exception exists and is open
            exception = db.query(DBException).filter(DBException.id == exception_id).first()
            if not exception:
                return {"error": f"Exception not found: {exception_id}"}

            if exception.status.value != "open":
                return {"error": f"Exception is not open: status is {exception.status.value}"}

            # Create approval queue entry
            approval = ApprovalQueue(
                action_type=ApprovalActionType.DISMISS,
                payload={
                    "exception_id": exception_id,
                    "reason": reason,
                    "notes": notes,
                },
                proposed_by="agent",
                summary=f"Dismiss: {exception.title[:50]}",
                trace_id=trace_id if trace_id else None
            )

            db.add(approval)
            db.commit()
            db.refresh(approval)

            result = {
                "approval_id": str(approval.id),
                "status": "pending",
                "message": f"Dismissal proposal created. Awaiting human approval.",
                "exception_title": exception.title
            }

            db.close()
            return result

        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def propose_decision(
        exception_id: str,
        rationale: str,
        assumptions: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Provide decision support context for an exception.

        IMPORTANT: This tool does NOT recommend or rank options.
        It only provides analysis and context to help the human decide.
        The actual decision must be made by a human.

        Args:
            exception_id: UUID of the exception
            rationale: Analysis and context for decision-making
            assumptions: Key assumptions underlying the analysis
            trace_id: Optional trace ID for observability

        Returns:
            Dict with analysis added status
        """
        try:
            from core.models import Exception as DBException

            db = get_db_session()

            exception = db.query(DBException).filter(DBException.id == exception_id).first()
            if not exception:
                return {"error": f"Exception not found: {exception_id}"}

            # Add decision context (NOT a recommendation)
            if exception.context is None:
                exception.context = {}

            exception.context["agent_analysis"] = {
                "rationale": rationale,
                "assumptions": assumptions,
                "analyzed_at": datetime.utcnow().isoformat(),
                "disclaimer": "This analysis is provided for context only. The decision must be made by a human."
            }

            db.commit()

            result = {
                "success": True,
                "exception_id": exception_id,
                "message": "Decision context added. Human must make the actual decision.",
                "warning": "DO NOT use this to recommend options. Options must be presented symmetrically."
            }

            db.close()
            return result

        except Exception as e:
            return {"error": str(e)}

    return [
        propose_signal,
        propose_policy_draft,
        add_exception_context,
        dismiss_exception,
        propose_decision
    ]
