"""
Evidence Generator Service.

Generates deterministic, self-contained audit-grade evidence packs.
"""

from typing import Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from core.models import (
    EvidencePack, Decision, Exception, Evaluation, Signal,
    AuditEvent, AuditEventType
)
from core.domain.fingerprinting import compute_content_hash


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

        # Update decision with evidence pack link
        decision.evidence_pack_id = evidence_pack.id

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
            format: Export format ("json" only for Sprint 1; "pdf" in Sprint 2+)

        Returns:
            Bytes of exported pack

        Raises:
            ValueError: If pack not found or format unsupported
        """
        pack = (
            self.db.query(EvidencePack)
            .filter(EvidencePack.id == evidence_pack_id)
            .first()
        )

        if not pack:
            raise ValueError(f"Evidence pack {evidence_pack_id} not found")

        if format != "json":
            raise ValueError(f"Format '{format}' not supported in Sprint 1")

        # Export as pretty-printed JSON
        import json
        json_str = json.dumps(pack.evidence, indent=2, sort_keys=True)
        return json_str.encode('utf-8')

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
