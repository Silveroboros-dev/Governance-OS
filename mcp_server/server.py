"""
MCP Server - FastMCP server exposing governance kernel tools.

This server provides read-only access to:
- Open exceptions requiring decisions
- Policy definitions and versions
- Evidence packs for decisions
- Decision history and audit trail

SAFETY: v0 is READ-ONLY. No write tools are exposed.
All modifications must go through the UI with human approval.
"""

import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import FastMCP

# Initialize MCP server
mcp = FastMCP(
    "governance-os",
    instructions="""
    Governance OS MCP Server - Access to governance kernel with gated writes.

    READ TOOLS:
    - get_open_exceptions: List exceptions requiring human decisions
    - get_exception_detail: Get full context for a specific exception
    - get_policies: List active policies
    - get_evidence_pack: Get complete evidence for a decision
    - search_decisions: Search decision history
    - get_recent_signals: Get recent signals

    WRITE TOOLS (Sprint 3 - all require human approval):
    - propose_signal: Propose a candidate signal for human review
    - propose_policy_draft: Propose a draft policy for human review
    - add_exception_context: Enrich exception with additional context (no approval needed)
    - dismiss_exception: Propose dismissing an exception for human review
    - propose_decision: Provide decision context (NOT recommendations)

    SAFETY RULES:
    - All write operations go through approval queue for human review
    - Never recommend or rank options - present them symmetrically
    - All claims in narratives MUST reference evidence IDs
    - Confidence scores must be honest - don't inflate them
    """
)


def get_db_session():
    """Get database session for queries."""
    # Import here to avoid circular dependencies
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://governance:governance@localhost:5432/governance"
    )
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


# ============================================================================
# EXCEPTION TOOLS
# ============================================================================

@mcp.tool()
def get_open_exceptions(
    pack: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get open exceptions requiring human decisions.

    Args:
        pack: Filter by domain pack (treasury, wealth). Optional.
        severity: Filter by severity (low, medium, high, critical). Optional.
        limit: Maximum number of exceptions to return. Default 50.

    Returns:
        List of exception summaries with id, title, severity, raised_at, context.
    """
    try:
        from core.models import Exception as DBException

        db = get_db_session()
        query = db.query(DBException).filter(DBException.status == "open")

        if severity:
            query = query.filter(DBException.severity == severity)

        query = query.order_by(DBException.raised_at.desc()).limit(limit)

        exceptions = []
        for exc in query.all():
            exceptions.append({
                "id": str(exc.id),
                "title": exc.title,
                "severity": exc.severity.value if hasattr(exc.severity, 'value') else exc.severity,
                "status": exc.status.value if hasattr(exc.status, 'value') else exc.status,
                "raised_at": exc.raised_at.isoformat(),
                "context": exc.context or {},
                "policy_id": str(exc.policy_id) if exc.policy_id else None,
            })

        db.close()
        return exceptions

    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_exception_detail(exception_id: str) -> Dict[str, Any]:
    """
    Get full details for a specific exception including options and signals.

    Args:
        exception_id: UUID of the exception.

    Returns:
        Complete exception details including:
        - Exception metadata (title, severity, status, context)
        - Available options (symmetric, no recommendations)
        - Contributing signals
        - Related evaluation details
    """
    try:
        from core.models import Exception as DBException, ExceptionOption, Signal, Evaluation

        db = get_db_session()
        exc = db.query(DBException).filter(DBException.id == exception_id).first()

        if not exc:
            return {"error": f"Exception not found: {exception_id}"}

        # Get options
        options = []
        for opt in db.query(ExceptionOption).filter(ExceptionOption.exception_id == exc.id).all():
            options.append({
                "id": str(opt.id),
                "label": opt.label,
                "description": opt.description,
                "implications": opt.implications or [],
            })

        # Get signals
        signals = []
        if exc.signal_ids:
            for signal_id in exc.signal_ids:
                signal = db.query(Signal).filter(Signal.id == signal_id).first()
                if signal:
                    signals.append({
                        "id": str(signal.id),
                        "signal_type": signal.signal_type,
                        "source": signal.source,
                        "payload": signal.payload,
                        "timestamp": signal.timestamp.isoformat(),
                        "reliability": signal.reliability,
                    })

        # Get evaluation if exists
        evaluation = None
        if exc.evaluation_id:
            eval = db.query(Evaluation).filter(Evaluation.id == exc.evaluation_id).first()
            if eval:
                evaluation = {
                    "id": str(eval.id),
                    "result": eval.result.value if hasattr(eval.result, 'value') else eval.result,
                    "details": eval.details or {},
                    "input_hash": eval.input_hash,
                }

        result = {
            "id": str(exc.id),
            "title": exc.title,
            "severity": exc.severity.value if hasattr(exc.severity, 'value') else exc.severity,
            "status": exc.status.value if hasattr(exc.status, 'value') else exc.status,
            "raised_at": exc.raised_at.isoformat(),
            "context": exc.context or {},
            "fingerprint": exc.fingerprint,
            "options": options,
            "signals": signals,
            "evaluation": evaluation,
            "policy_id": str(exc.policy_id) if exc.policy_id else None,
        }

        db.close()
        return result

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# POLICY TOOLS
# ============================================================================

@mcp.tool()
def get_policies(
    is_active: bool = True,
    include_versions: bool = False
) -> List[Dict[str, Any]]:
    """
    Get policy definitions.

    Args:
        is_active: Only return active policies. Default True.
        include_versions: Include version history. Default False.

    Returns:
        List of policies with id, name, description, current version.
    """
    try:
        from core.models import Policy, PolicyVersion

        db = get_db_session()
        query = db.query(Policy)

        if is_active:
            query = query.filter(Policy.is_active == True)

        policies = []
        for policy in query.all():
            policy_data = {
                "id": str(policy.id),
                "name": policy.name,
                "description": policy.description,
                "is_active": policy.is_active,
                "created_at": policy.created_at.isoformat(),
            }

            # Get current version
            current_version = db.query(PolicyVersion).filter(
                PolicyVersion.policy_id == policy.id,
                PolicyVersion.is_current == True
            ).first()

            if current_version:
                policy_data["current_version"] = {
                    "id": str(current_version.id),
                    "version_number": current_version.version_number,
                    "rule_definition": current_version.rule_definition,
                    "effective_from": current_version.effective_from.isoformat() if current_version.effective_from else None,
                }

            if include_versions:
                versions = db.query(PolicyVersion).filter(
                    PolicyVersion.policy_id == policy.id
                ).order_by(PolicyVersion.version_number.desc()).all()

                policy_data["versions"] = [
                    {
                        "id": str(v.id),
                        "version_number": v.version_number,
                        "is_current": v.is_current,
                        "effective_from": v.effective_from.isoformat() if v.effective_from else None,
                        "change_reason": v.change_reason,
                    }
                    for v in versions
                ]

            policies.append(policy_data)

        db.close()
        return policies

    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def get_policy_detail(policy_id: str) -> Dict[str, Any]:
    """
    Get full details for a specific policy including rule definition.

    Args:
        policy_id: UUID of the policy.

    Returns:
        Complete policy details including current rule definition.
    """
    try:
        from core.models import Policy, PolicyVersion

        db = get_db_session()
        policy = db.query(Policy).filter(Policy.id == policy_id).first()

        if not policy:
            return {"error": f"Policy not found: {policy_id}"}

        current_version = db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy.id,
            PolicyVersion.is_current == True
        ).first()

        result = {
            "id": str(policy.id),
            "name": policy.name,
            "description": policy.description,
            "is_active": policy.is_active,
            "created_at": policy.created_at.isoformat(),
        }

        if current_version:
            result["current_version"] = {
                "id": str(current_version.id),
                "version_number": current_version.version_number,
                "rule_definition": current_version.rule_definition,
                "effective_from": current_version.effective_from.isoformat() if current_version.effective_from else None,
                "effective_to": current_version.effective_to.isoformat() if current_version.effective_to else None,
                "change_reason": current_version.change_reason,
            }

        db.close()
        return result

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# EVIDENCE TOOLS
# ============================================================================

@mcp.tool()
def get_evidence_pack(decision_id: str) -> Dict[str, Any]:
    """
    Get complete evidence pack for a decision.

    This is the primary tool for grounding narrative claims.
    All claims in generated memos MUST reference evidence_ids from this pack.

    Args:
        decision_id: UUID of the decision.

    Returns:
        Evidence pack containing:
        - Decision metadata (chosen option, rationale, assumptions)
        - Exception context
        - Policy version used
        - Contributing signals with full payloads
        - Evaluation details
        - Audit trail
    """
    try:
        from core.models import (
            Decision, Exception as DBException, ExceptionOption,
            Policy, PolicyVersion, Signal, Evaluation, AuditEvent
        )

        db = get_db_session()
        decision = db.query(Decision).filter(Decision.id == decision_id).first()

        if not decision:
            return {"error": f"Decision not found: {decision_id}"}

        # Build evidence pack
        evidence = {
            "evidence_pack_id": f"evp_{decision_id}",
            "generated_at": datetime.utcnow().isoformat(),
            "decision": {
                "id": str(decision.id),
                "decided_at": decision.decided_at.isoformat(),
                "decided_by": decision.decided_by,
                "rationale": decision.rationale,
                "assumptions": decision.assumptions,
            },
            "evidence_items": []
        }

        # Add chosen option
        if decision.chosen_option_id:
            option = db.query(ExceptionOption).filter(
                ExceptionOption.id == decision.chosen_option_id
            ).first()
            if option:
                evidence["decision"]["chosen_option"] = {
                    "id": str(option.id),
                    "label": option.label,
                    "description": option.description,
                }
                evidence["evidence_items"].append({
                    "evidence_id": f"opt_{option.id}",
                    "type": "chosen_option",
                    "data": {
                        "label": option.label,
                        "description": option.description,
                        "implications": option.implications,
                    }
                })

        # Add exception context
        if decision.exception_id:
            exc = db.query(DBException).filter(DBException.id == decision.exception_id).first()
            if exc:
                evidence["exception"] = {
                    "id": str(exc.id),
                    "title": exc.title,
                    "severity": exc.severity.value if hasattr(exc.severity, 'value') else exc.severity,
                    "context": exc.context,
                    "raised_at": exc.raised_at.isoformat(),
                }
                evidence["evidence_items"].append({
                    "evidence_id": f"exc_{exc.id}",
                    "type": "exception_context",
                    "data": exc.context or {}
                })

                # Add signals
                if exc.signal_ids:
                    for signal_id in exc.signal_ids:
                        signal = db.query(Signal).filter(Signal.id == signal_id).first()
                        if signal:
                            evidence["evidence_items"].append({
                                "evidence_id": f"sig_{signal.id}",
                                "type": "signal",
                                "data": {
                                    "signal_type": signal.signal_type,
                                    "source": signal.source,
                                    "payload": signal.payload,
                                    "timestamp": signal.timestamp.isoformat(),
                                    "reliability": signal.reliability,
                                }
                            })

                # Add evaluation
                if exc.evaluation_id:
                    eval = db.query(Evaluation).filter(Evaluation.id == exc.evaluation_id).first()
                    if eval:
                        evidence["evaluation"] = {
                            "id": str(eval.id),
                            "result": eval.result.value if hasattr(eval.result, 'value') else eval.result,
                            "details": eval.details,
                            "input_hash": eval.input_hash,
                        }
                        evidence["evidence_items"].append({
                            "evidence_id": f"eval_{eval.id}",
                            "type": "evaluation",
                            "data": eval.details or {}
                        })

                # Add policy
                if exc.policy_id:
                    policy = db.query(Policy).filter(Policy.id == exc.policy_id).first()
                    if policy:
                        version = db.query(PolicyVersion).filter(
                            PolicyVersion.policy_id == policy.id,
                            PolicyVersion.is_current == True
                        ).first()

                        evidence["policy"] = {
                            "id": str(policy.id),
                            "name": policy.name,
                            "description": policy.description,
                        }
                        if version:
                            evidence["policy"]["version"] = {
                                "id": str(version.id),
                                "version_number": version.version_number,
                                "rule_definition": version.rule_definition,
                            }
                            evidence["evidence_items"].append({
                                "evidence_id": f"pol_{policy.id}",
                                "type": "policy",
                                "data": {
                                    "name": policy.name,
                                    "rule_definition": version.rule_definition,
                                }
                            })

        # Add audit events
        audit_events = db.query(AuditEvent).filter(
            AuditEvent.decision_id == decision.id
        ).order_by(AuditEvent.timestamp.asc()).all()

        evidence["audit_trail"] = [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "actor": event.actor,
                "details": event.details,
            }
            for event in audit_events
        ]

        db.close()
        return evidence

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_decisions(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    decided_by: Optional[str] = None,
    policy_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search decision history.

    Args:
        from_date: Start date (ISO format). Optional.
        to_date: End date (ISO format). Optional.
        decided_by: Filter by decision maker. Optional.
        policy_id: Filter by policy. Optional.
        limit: Maximum results. Default 50.

    Returns:
        List of decision summaries.
    """
    try:
        from core.models import Decision, Exception as DBException

        db = get_db_session()
        query = db.query(Decision)

        if from_date:
            query = query.filter(Decision.decided_at >= datetime.fromisoformat(from_date))
        if to_date:
            query = query.filter(Decision.decided_at <= datetime.fromisoformat(to_date))
        if decided_by:
            query = query.filter(Decision.decided_by == decided_by)

        query = query.order_by(Decision.decided_at.desc()).limit(limit)

        decisions = []
        for dec in query.all():
            # Get exception for context
            exc = db.query(DBException).filter(DBException.id == dec.exception_id).first()

            decisions.append({
                "id": str(dec.id),
                "decided_at": dec.decided_at.isoformat(),
                "decided_by": dec.decided_by,
                "rationale": dec.rationale[:200] + "..." if len(dec.rationale or "") > 200 else dec.rationale,
                "exception": {
                    "id": str(exc.id) if exc else None,
                    "title": exc.title if exc else None,
                    "severity": exc.severity.value if exc and hasattr(exc.severity, 'value') else (exc.severity if exc else None),
                } if exc else None,
            })

        db.close()
        return decisions

    except Exception as e:
        return [{"error": str(e)}]


# ============================================================================
# SIGNAL TOOLS
# ============================================================================

@mcp.tool()
def get_recent_signals(
    signal_type: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get recent signals.

    Args:
        signal_type: Filter by signal type. Optional.
        source: Filter by source. Optional.
        limit: Maximum results. Default 50.

    Returns:
        List of recent signals with payloads.
    """
    try:
        from core.models import Signal

        db = get_db_session()
        query = db.query(Signal)

        if signal_type:
            query = query.filter(Signal.signal_type == signal_type)
        if source:
            query = query.filter(Signal.source == source)

        query = query.order_by(Signal.timestamp.desc()).limit(limit)

        signals = []
        for sig in query.all():
            signals.append({
                "id": str(sig.id),
                "signal_type": sig.signal_type,
                "source": sig.source,
                "payload": sig.payload,
                "timestamp": sig.timestamp.isoformat(),
                "reliability": sig.reliability,
            })

        db.close()
        return signals

    except Exception as e:
        return [{"error": str(e)}]


# ============================================================================
# WRITE TOOLS (Sprint 3)
# ============================================================================

# Import and register write tools
from mcp_server.tools.write_tools import register_write_tools
write_tools = register_write_tools(mcp)


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

def create_server():
    """Create and return the MCP server instance."""
    return mcp


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
