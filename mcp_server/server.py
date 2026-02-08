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
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import FastMCP
from starlette.responses import JSONResponse, HTMLResponse
from starlette.requests import Request

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


# ============================================================================
# INFO ENDPOINT (for browser access)
# ============================================================================

@mcp.custom_route("/", methods=["GET"])
@mcp.custom_route("/info", methods=["GET"])
async def mcp_info(request: Request) -> HTMLResponse:
    """Return human-readable info page when accessed via browser."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Governance OS - MCP API</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 800px; margin: 40px auto; padding: 20px;
               background: #0a0a0b; color: #fafafa; }
        h1 { color: #22c55e; }
        code { background: #18181b; padding: 2px 8px; border-radius: 4px; }
        pre { background: #18181b; padding: 16px; border-radius: 8px; overflow-x: auto; }
        a { color: #22c55e; }
        .tool { margin: 12px 0; padding: 12px; background: #111113; border-radius: 6px; }
        .tool-name { font-weight: 600; color: #22c55e; }
        .tool-desc { color: #a1a1aa; font-size: 14px; }
    </style>
</head>
<body>
    <h1>Governance OS MCP Server</h1>
    <p>This is an <a href="https://modelcontextprotocol.io">MCP (Model Context Protocol)</a> server
       that exposes the Governance OS kernel to AI agents.</p>

    <h2>Connection</h2>
    <p>Connect using any MCP client with Streamable HTTP transport:</p>
    <pre>URL: https://govos-mcp-1064412167254.europe-west4.run.app/mcp
Transport: Streamable HTTP</pre>

    <h2>Available Tools</h2>
    <div class="tool">
        <div class="tool-name">get_open_exceptions</div>
        <div class="tool-desc">List exceptions requiring human decisions</div>
    </div>
    <div class="tool">
        <div class="tool-name">get_exception_detail</div>
        <div class="tool-desc">Get full context for a specific exception</div>
    </div>
    <div class="tool">
        <div class="tool-name">get_policies</div>
        <div class="tool-desc">List active policies</div>
    </div>
    <div class="tool">
        <div class="tool-name">get_policy_detail</div>
        <div class="tool-desc">Get full details for a specific policy</div>
    </div>
    <div class="tool">
        <div class="tool-name">get_evidence_pack</div>
        <div class="tool-desc">Get complete evidence pack for a decision</div>
    </div>
    <div class="tool">
        <div class="tool-name">search_decisions</div>
        <div class="tool-desc">Search decision history</div>
    </div>
    <div class="tool">
        <div class="tool-name">get_recent_signals</div>
        <div class="tool-desc">Get recent signals</div>
    </div>

    <h2>Resources</h2>
    <ul>
        <li><a href="https://github.com/Silveroboros-dev/Governance-OS">GitHub Repository</a></li>
        <li><a href="https://governance-os.web.app">Landing Page</a></li>
        <li><a href="https://web--governance-os.europe-west4.hosted.app">Interactive Demo</a></li>
    </ul>

    <p style="color: #71717a; margin-top: 40px; font-size: 14px;">
        v0 is read-only. Write tools coming in Sprint 3.
    </p>
</body>
</html>"""
    return HTMLResponse(content=html)


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
    from core.models import Exception as DBException

    db = get_db_session()
    try:
        query = db.query(DBException).filter(DBException.status == "open")

        if severity:
            query = query.filter(DBException.severity == severity)

        query = query.order_by(DBException.raised_at.desc()).limit(limit)

        exceptions = []
        for exc in query.all():
            # Get policy info from evaluation
            policy_id = None
            policy_name = None
            if exc.evaluation and exc.evaluation.policy_version and exc.evaluation.policy_version.policy:
                policy_id = str(exc.evaluation.policy_version.policy.id)
                policy_name = exc.evaluation.policy_version.policy.name

            exceptions.append({
                "id": str(exc.id),
                "title": exc.title,
                "severity": exc.severity.value if hasattr(exc.severity, 'value') else exc.severity,
                "status": exc.status.value if hasattr(exc.status, 'value') else exc.status,
                "raised_at": exc.raised_at.isoformat(),
                "context": exc.context or {},
                "policy_id": policy_id,
                "policy_name": policy_name,
            })

        return exceptions

    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


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
    from core.models import Exception as DBException, Signal, Evaluation

    db = get_db_session()
    try:
        exc = db.query(DBException).filter(DBException.id == exception_id).first()

        if not exc:
            return {"error": f"Exception not found: {exception_id}"}

        # Options are stored as JSONB in the exception model
        # Structure: [{"id": "...", "label": "...", "description": "...", "implications": [...]}, ...]
        options = exc.options or []

        # Get signals from evaluation
        signals = []
        if exc.evaluation and exc.evaluation.signal_ids:
            for signal_id in exc.evaluation.signal_ids:
                signal = db.query(Signal).filter(Signal.id == signal_id).first()
                if signal:
                    signals.append({
                        "id": str(signal.id),
                        "signal_type": signal.signal_type,
                        "source": signal.source,
                        "payload": signal.payload,
                        "timestamp": signal.observed_at.isoformat() if signal.observed_at else None,
                        "reliability": signal.reliability.value if hasattr(signal.reliability, 'value') else signal.reliability,
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

        # Get policy info from evaluation
        policy_info = None
        if exc.evaluation and exc.evaluation.policy_version:
            pv = exc.evaluation.policy_version
            if pv.policy:
                policy_info = {
                    "id": str(pv.policy.id),
                    "name": pv.policy.name,
                    "version_number": pv.version_number,
                }

        return {
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
            "policy": policy_info,
        }

    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


# ============================================================================
# POLICY TOOLS
# ============================================================================

@mcp.tool()
def get_policies(
    pack: Optional[str] = None,
    active_only: bool = True,
    include_versions: bool = False
) -> List[Dict[str, Any]]:
    """
    Get policy definitions.

    Args:
        pack: Filter by domain pack (treasury, wealth). Optional.
        active_only: Only return policies with an active version. Default True.
        include_versions: Include version history. Default False.

    Returns:
        List of policies with id, name, description, current version.
    """
    from core.models import Policy, PolicyVersion

    db = get_db_session()
    try:
        query = db.query(Policy)

        if pack:
            query = query.filter(Policy.pack == pack)

        policies = []
        for policy in query.all():
            # Get current (active) version
            current_version = db.query(PolicyVersion).filter(
                PolicyVersion.policy_id == policy.id,
                PolicyVersion.status == "active"
            ).order_by(PolicyVersion.version_number.desc()).first()

            if active_only and not current_version:
                continue

            policy_data = {
                "id": str(policy.id),
                "name": policy.name,
                "pack": policy.pack,
                "description": policy.description,
                "created_at": policy.created_at.isoformat(),
            }

            if current_version:
                policy_data["current_version"] = {
                    "id": str(current_version.id),
                    "version_number": current_version.version_number,
                    "status": current_version.status.value if hasattr(current_version.status, 'value') else current_version.status,
                    "rule_definition": current_version.rule_definition,
                    "valid_from": current_version.valid_from.isoformat() if current_version.valid_from else None,
                }

            if include_versions:
                versions = db.query(PolicyVersion).filter(
                    PolicyVersion.policy_id == policy.id
                ).order_by(PolicyVersion.version_number.desc()).all()

                policy_data["versions"] = [
                    {
                        "id": str(v.id),
                        "version_number": v.version_number,
                        "status": v.status.value if hasattr(v.status, 'value') else v.status,
                        "valid_from": v.valid_from.isoformat() if v.valid_from else None,
                        "changelog": v.changelog,
                    }
                    for v in versions
                ]

            policies.append(policy_data)

        return policies

    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


@mcp.tool()
def get_policy_detail(policy_id: str) -> Dict[str, Any]:
    """
    Get full details for a specific policy including rule definition.

    Args:
        policy_id: UUID of the policy.

    Returns:
        Complete policy details including current rule definition.
    """
    from core.models import Policy, PolicyVersion

    db = get_db_session()
    try:
        policy = db.query(Policy).filter(Policy.id == policy_id).first()

        if not policy:
            return {"error": f"Policy not found: {policy_id}"}

        current_version = db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy.id,
            PolicyVersion.status == "active"
        ).order_by(PolicyVersion.version_number.desc()).first()

        result = {
            "id": str(policy.id),
            "name": policy.name,
            "pack": policy.pack,
            "description": policy.description,
            "created_at": policy.created_at.isoformat(),
        }

        if current_version:
            result["current_version"] = {
                "id": str(current_version.id),
                "version_number": current_version.version_number,
                "status": current_version.status.value if hasattr(current_version.status, 'value') else current_version.status,
                "rule_definition": current_version.rule_definition,
                "valid_from": current_version.valid_from.isoformat() if current_version.valid_from else None,
                "valid_to": current_version.valid_to.isoformat() if current_version.valid_to else None,
                "changelog": current_version.changelog,
            }

        return result

    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


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
    from core.models import (
        Decision, Exception as DBException,
        Policy, PolicyVersion, Signal, Evaluation, AuditEvent
    )

    db = get_db_session()
    try:
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

        # Get exception for context and options
        exc = None
        if decision.exception_id:
            exc = db.query(DBException).filter(DBException.id == decision.exception_id).first()

        # Add chosen option (options are stored as JSONB in exception)
        if decision.chosen_option_id and exc and exc.options:
            # Find the chosen option from the exception's options array
            for opt in exc.options:
                if opt.get("id") == decision.chosen_option_id:
                    evidence["decision"]["chosen_option"] = {
                        "id": opt.get("id"),
                        "label": opt.get("label"),
                        "description": opt.get("description"),
                    }
                    evidence["evidence_items"].append({
                        "evidence_id": f"opt_{opt.get('id')}",
                        "type": "chosen_option",
                        "data": {
                            "label": opt.get("label"),
                            "description": opt.get("description"),
                            "implications": opt.get("implications", []),
                        }
                    })
                    break

        # Add exception context
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

            # Get evaluation and signals from evaluation
            if exc.evaluation_id:
                eval_obj = db.query(Evaluation).filter(Evaluation.id == exc.evaluation_id).first()
                if eval_obj:
                    evidence["evaluation"] = {
                        "id": str(eval_obj.id),
                        "result": eval_obj.result.value if hasattr(eval_obj.result, 'value') else eval_obj.result,
                        "details": eval_obj.details,
                        "input_hash": eval_obj.input_hash,
                    }
                    evidence["evidence_items"].append({
                        "evidence_id": f"eval_{eval_obj.id}",
                        "type": "evaluation",
                        "data": eval_obj.details or {}
                    })

                    # Add signals from evaluation
                    if eval_obj.signal_ids:
                        for signal_id in eval_obj.signal_ids:
                            signal = db.query(Signal).filter(Signal.id == signal_id).first()
                            if signal:
                                evidence["evidence_items"].append({
                                    "evidence_id": f"sig_{signal.id}",
                                    "type": "signal",
                                    "data": {
                                        "signal_type": signal.signal_type,
                                        "source": signal.source,
                                        "payload": signal.payload,
                                        "timestamp": signal.observed_at.isoformat() if signal.observed_at else None,
                                        "reliability": signal.reliability.value if hasattr(signal.reliability, 'value') else signal.reliability,
                                    }
                                })

                    # Add policy from evaluation's policy_version
                    if eval_obj.policy_version:
                        pv = eval_obj.policy_version
                        policy = pv.policy
                        if policy:
                            evidence["policy"] = {
                                "id": str(policy.id),
                                "name": policy.name,
                                "description": policy.description,
                            }
                            evidence["policy"]["version"] = {
                                "id": str(pv.id),
                                "version_number": pv.version_number,
                                "rule_definition": pv.rule_definition,
                            }
                            evidence["evidence_items"].append({
                                "evidence_id": f"pol_{policy.id}",
                                "type": "policy",
                                "data": {
                                    "name": policy.name,
                                    "rule_definition": pv.rule_definition,
                                }
                            })

        # Add audit events (query by aggregate_id = decision.id)
        audit_events = db.query(AuditEvent).filter(
            AuditEvent.aggregate_id == decision.id
        ).order_by(AuditEvent.occurred_at.asc()).all()

        evidence["audit_trail"] = [
            {
                "id": str(event.id),
                "event_type": event.event_type.value if hasattr(event.event_type, 'value') else event.event_type,
                "timestamp": event.occurred_at.isoformat(),
                "actor": event.actor,
                "details": event.event_data,
            }
            for event in audit_events
        ]

        return evidence

    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


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
    from core.models import Decision, Exception as DBException

    db = get_db_session()
    try:
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

        return decisions

    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


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
    from core.models import Signal

    db = get_db_session()
    try:
        query = db.query(Signal)

        if signal_type:
            query = query.filter(Signal.signal_type == signal_type)
        if source:
            query = query.filter(Signal.source == source)

        query = query.order_by(Signal.observed_at.desc()).limit(limit)

        signals = []
        for sig in query.all():
            signals.append({
                "id": str(sig.id),
                "signal_type": sig.signal_type,
                "pack": sig.pack,
                "source": sig.source,
                "payload": sig.payload,
                "observed_at": sig.observed_at.isoformat(),
                "ingested_at": sig.ingested_at.isoformat() if sig.ingested_at else None,
                "reliability": sig.reliability.value if hasattr(sig.reliability, 'value') else sig.reliability,
            })

        return signals

    except Exception as e:
        return [{"error": str(e)}]
    finally:
        db.close()


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
    """Run the MCP server.

    Supports multiple transports:
    - stdio (default): For local Claude Desktop integration
    - http: For Cloud Run deployment (Streamable HTTP via uvicorn)
    - sse: Legacy SSE transport (via uvicorn)

    Set MCP_TRANSPORT env var to control transport.
    Set MCP_HOST and MCP_PORT for network transports.
    """
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))

    if transport in ("http", "streamable-http"):
        # Streamable HTTP for Cloud Run - serve ASGI app with uvicorn
        import uvicorn
        app = mcp.streamable_http_app()
        uvicorn.run(app, host=host, port=port)
    elif transport == "sse":
        # Legacy SSE transport - serve ASGI app with uvicorn
        import uvicorn
        app = mcp.sse_app()
        uvicorn.run(app, host=host, port=port)
    else:
        # Default stdio for local Claude Desktop
        mcp.run()


if __name__ == "__main__":
    main()
