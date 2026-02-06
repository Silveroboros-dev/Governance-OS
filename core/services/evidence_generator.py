"""
Evidence Generator Service.

Generates deterministic, self-contained audit-grade evidence packs.
"""

import time
from typing import Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.models import (
    EvidencePack, Decision, Exception, Evaluation, Signal,
    AuditEvent, AuditEventType
)
from core.domain.fingerprinting import compute_content_hash
from core.logging import get_logger

logger = get_logger(__name__)


class EvidenceGenerator:
    """
    Evidence pack generation service.

    Creates self-contained JSON documents with complete audit trail:
    - Decision and rationale
    - Exception context
    - Evaluation details
    - All contributing signals
    - Policy version
    - Complete audit trail

    Evidence packs are DETERMINISTIC: same decision → same pack.
    """

    def __init__(self, db: Session):
        """
        Initialize evidence generator.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def generate_pack(self, decision: Decision) -> EvidencePack:
        """
        Generate complete evidence pack for a decision.

        The pack is self-contained and includes ALL data needed to
        understand and audit the decision.

        Args:
            decision: Decision object

        Returns:
            EvidencePack object

        Example:
            >>> generator = EvidenceGenerator(db)
            >>> pack = generator.generate_pack(decision)
            >>> pack.content_hash
            'a1b2c3d4...'
            >>> pack.evidence.keys()
            dict_keys(['decision', 'exception', 'evaluation', 'signals', 'policy', 'audit_trail'])
        """
        start_time = time.time()

        # Fetch related data
        exception = decision.exception
        evaluation = exception.evaluation
        policy_version = evaluation.policy_version
        policy = policy_version.policy

        # Fetch signals
        signals = (
            self.db.query(Signal)
            .filter(Signal.id.in_(evaluation.signal_ids))
            .all()
        )

        # Fetch audit trail
        audit_events = self._fetch_audit_trail(decision, exception, evaluation)

        # Build evidence document
        evidence = {
            "decision": {
                "id": str(decision.id),
                "chosen_option_id": decision.chosen_option_id,
                "rationale": decision.rationale,
                "assumptions": decision.assumptions,
                "decided_by": decision.decided_by,
                "decided_at": decision.decided_at.isoformat()
            },
            "exception": {
                "id": str(exception.id),
                "title": exception.title,
                "severity": exception.severity.value,
                "context": exception.context,
                "options": exception.options,
                "raised_at": exception.raised_at.isoformat(),
                "resolved_at": exception.resolved_at.isoformat() if exception.resolved_at else None,
                "fingerprint": exception.fingerprint
            },
            "evaluation": {
                "id": str(evaluation.id),
                "result": evaluation.result.value,
                "details": evaluation.details,
                "evaluated_at": evaluation.evaluated_at.isoformat(),
                "input_hash": evaluation.input_hash
            },
            "policy": {
                "id": str(policy.id),
                "name": policy.name,
                "pack": policy.pack,
                "description": policy.description,
                "version": {
                    "id": str(policy_version.id),
                    "version_number": policy_version.version_number,
                    "rule_definition": policy_version.rule_definition,
                    "valid_from": policy_version.valid_from.isoformat(),
                    "valid_to": policy_version.valid_to.isoformat() if policy_version.valid_to else None
                }
            },
            "signals": [
                {
                    "id": str(signal.id),
                    "signal_type": signal.signal_type,
                    "payload": signal.payload,
                    "source": signal.source,
                    "reliability": signal.reliability.value,
                    "observed_at": signal.observed_at.isoformat(),
                    "metadata": signal.signal_metadata
                }
                for signal in signals
            ],
            "audit_trail": audit_events,
            "metadata": {
                "pack_version": "1.0",
                "generated_for_decision": str(decision.id)
            }
        }

        # Compute content hash (deterministic)
        content_hash = compute_content_hash(evidence)

        # Create or update evidence pack
        existing_pack = (
            self.db.query(EvidencePack)
            .filter(EvidencePack.decision_id == decision.id)
            .first()
        )

        if existing_pack:
            # Pack already exists - return it (idempotent)
            return existing_pack

        # Create new pack
        evidence_pack = EvidencePack(
            decision_id=decision.id,
            evidence=evidence,
            content_hash=content_hash
        )

        self.db.add(evidence_pack)
        self.db.flush()  # Flush to generate evidence_pack.id before using it

        # Note: We don't update decision.evidence_pack_id because decisions table
        # is immutable (has database triggers preventing UPDATE). The link is
        # through EvidencePack.decision_id instead.

        # Create audit event
        audit_event = AuditEvent(
            event_type=AuditEventType.EVIDENCE_PACK_GENERATED,
            aggregate_type="evidence_pack",
            aggregate_id=evidence_pack.id,
            event_data={
                "decision_id": str(decision.id),
                "content_hash": content_hash,
                "signal_count": len(signals)
            },
            actor="system"
        )

        self.db.add(audit_event)
        self.db.commit()

        duration_ms = (time.time() - start_time) * 1000
        logger.evidence_pack_generated(
            evidence_pack_id=evidence_pack.id,
            decision_id=decision.id,
            duration_ms=duration_ms
        )

        return evidence_pack

    def export_pack(
        self,
        evidence_pack_id: UUID,
        format: str = "json"
    ) -> bytes:
        """
        Export evidence pack for external consumption.

        Args:
            evidence_pack_id: UUID of the evidence pack
            format: Export format - "json", "html", or "pdf"

        Returns:
            Bytes of exported pack

        Raises:
            ValueError: If pack not found or format unsupported
            ImportError: If PDF requested but WeasyPrint not installed
        """
        pack = (
            self.db.query(EvidencePack)
            .filter(EvidencePack.id == evidence_pack_id)
            .first()
        )

        if not pack:
            raise ValueError(f"Evidence pack {evidence_pack_id} not found")

        if format == "json":
            # Export as pretty-printed JSON
            import json
            json_str = json.dumps(pack.evidence, indent=2, sort_keys=True)
            return json_str.encode("utf-8")

        elif format == "html":
            # Export as standalone HTML
            from core.services.evidence_renderer import EvidenceRenderer
            renderer = EvidenceRenderer()
            return renderer.render_html(pack).encode("utf-8")

        elif format == "pdf":
            # Export as PDF (requires WeasyPrint)
            from core.services.evidence_renderer import EvidenceRenderer
            renderer = EvidenceRenderer()
            return renderer.render_pdf(pack)

        else:
            raise ValueError(f"Format '{format}' not supported. Use 'json', 'html', or 'pdf'.")

    def _fetch_audit_trail(
        self,
        decision: Decision,
        exception: Exception,
        evaluation: Evaluation
    ) -> list[Dict[str, Any]]:
        """
        Fetch complete audit trail for the decision.

        Args:
            decision: Decision object
            exception: Exception object
            evaluation: Evaluation object

        Returns:
            List of audit event dictionaries
        """
        # Get all audit events related to this decision chain
        aggregate_ids = [
            evaluation.id,
            exception.id,
            decision.id
        ]

        events = (
            self.db.query(AuditEvent)
            .filter(AuditEvent.aggregate_id.in_(aggregate_ids))
            .order_by(AuditEvent.occurred_at)
            .all()
        )

        return [
            {
                "id": str(event.id),
                "event_type": event.event_type.value,
                "aggregate_type": event.aggregate_type,
                "aggregate_id": str(event.aggregate_id),
                "event_data": event.event_data,
                "actor": event.actor,
                "occurred_at": event.occurred_at.isoformat()
            }
            for event in events
        ]

    def format_for_narrative_agent(self, evidence_pack: EvidencePack) -> Dict[str, Any]:
        """
        Format evidence pack for NarrativeAgent consumption.

        Converts the internal evidence structure to the format expected by
        NarrativeAgent, with evidence_items array where each item has an
        evidence_id for claim grounding.

        Args:
            evidence_pack: EvidencePack object

        Returns:
            Dict in NarrativeAgent format with evidence_items array
        """
        evidence = evidence_pack.evidence
        evidence_items = []

        # Add signals
        for signal in evidence.get("signals", []):
            evidence_items.append({
                "evidence_id": f"sig_{signal['id'][:8]}",
                "type": "signal",
                "data": {
                    "signal_type": signal["signal_type"],
                    "payload": signal["payload"],
                    "source": signal["source"],
                    "reliability": signal["reliability"],
                    "observed_at": signal["observed_at"]
                }
            })

        # Add exception context
        exc = evidence.get("exception", {})
        if exc:
            evidence_items.append({
                "evidence_id": f"exc_{exc['id'][:8]}",
                "type": "exception_context",
                "data": {
                    "title": exc["title"],
                    "severity": exc["severity"],
                    "context": exc["context"],
                    "raised_at": exc["raised_at"],
                    "resolved_at": exc.get("resolved_at")
                }
            })

        # Add evaluation
        eval_data = evidence.get("evaluation", {})
        if eval_data:
            evidence_items.append({
                "evidence_id": f"eval_{eval_data['id'][:8]}",
                "type": "evaluation",
                "data": {
                    "result": eval_data["result"],
                    "details": eval_data["details"],
                    "evaluated_at": eval_data["evaluated_at"],
                    "input_hash": eval_data["input_hash"]
                }
            })

        # Add chosen option
        decision = evidence.get("decision", {})
        options = exc.get("options", [])
        chosen_option_id = decision.get("chosen_option_id")
        chosen_option = next((o for o in options if o.get("id") == chosen_option_id), None)
        if chosen_option:
            evidence_items.append({
                "evidence_id": f"opt_{chosen_option_id}",
                "type": "chosen_option",
                "data": {
                    "option_id": chosen_option_id,
                    "label": chosen_option.get("label", ""),
                    "description": chosen_option.get("description", ""),
                    "rationale": decision.get("rationale"),
                    "assumptions": decision.get("assumptions")
                }
            })

        # Add policy
        policy = evidence.get("policy", {})
        if policy:
            evidence_items.append({
                "evidence_id": f"pol_{policy['id'][:8]}",
                "type": "policy",
                "data": {
                    "name": policy["name"],
                    "pack": policy["pack"],
                    "description": policy["description"],
                    "version_number": policy.get("version", {}).get("version_number"),
                    "rule_definition": policy.get("version", {}).get("rule_definition")
                }
            })

        return {
            "evidence_pack_id": str(evidence_pack.id),
            "generated_at": evidence_pack.generated_at.isoformat(),
            "decision": {
                "id": decision.get("id"),
                "decided_at": decision.get("decided_at"),
                "decided_by": decision.get("decided_by"),
                "rationale": decision.get("rationale"),
                "assumptions": decision.get("assumptions")
            },
            "evidence_items": evidence_items
        }
