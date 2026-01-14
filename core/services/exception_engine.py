"""
Exception Engine Service.

Generates exceptions from failed evaluations with deduplication.
Ensures symmetric option presentation (NO RECOMMENDATIONS).
"""

from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models import (
    Exception, Evaluation, PolicyVersion, ExceptionSeverity,
    ExceptionStatus, EvaluationResult, AuditEvent, AuditEventType
)
from core.domain.fingerprinting import compute_exception_fingerprint
from core.logging import get_logger

logger = get_logger(__name__)


class ExceptionEngine:
    """
    Exception generation and deduplication engine.

    Creates exceptions when evaluations fail and require human judgment.
    Implements fingerprint-based deduplication to prevent duplicate exceptions.
    """

    def __init__(self, db: Session):
        """
        Initialize exception engine.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def generate_exception(
        self,
        evaluation: Evaluation,
        policy_version: PolicyVersion
    ) -> Optional[Exception]:
        """
        Generate exception from evaluation if needed.

        Returns None if:
        - Evaluation passed (no exception needed)
        - Duplicate exception already open (fingerprint match)

        CRITICAL: Options are ALWAYS symmetric (no ranking, no "recommended").

        Args:
            evaluation: Evaluation that may trigger exception
            policy_version: PolicyVersion that was evaluated

        Returns:
            Exception object or None

        Example:
            >>> exception = engine.generate_exception(evaluation, policy)
            >>> exception.severity
            'high'
            >>> len(exception.options)
            3
            >>> # All options have equal weight - NO RECOMMENDATIONS
        """
        # Check if exception is needed
        if evaluation.result != EvaluationResult.FAIL:
            logger.exception_not_needed(
                evaluation_id=evaluation.id,
                result=evaluation.result.value
            )
            return None  # Passed - no exception

        # Extract exception details from evaluation
        details = evaluation.details
        severity_str = details.get("severity", "medium")
        severity = self._map_severity(severity_str)

        # Generate fingerprint for deduplication
        key_dimensions = self._extract_key_dimensions(evaluation, policy_version)
        fingerprint = compute_exception_fingerprint(
            policy_version.policy_id,
            policy_version.rule_definition.get("type", "unknown"),
            key_dimensions
        )

        # Check for duplicate open exception
        existing = (
            self.db.query(Exception)
            .filter(
                Exception.fingerprint == fingerprint,
                Exception.status == ExceptionStatus.OPEN
            )
            .first()
        )

        if existing:
            # Duplicate - don't create new exception
            logger.exception_deduplicated(
                fingerprint=fingerprint,
                existing_exception_id=existing.id
            )
            return None

        # Generate context for UI
        context = self._generate_context(evaluation, policy_version)

        # Generate symmetric options (NO RANKING!)
        options = self._generate_options(evaluation, policy_version)

        # Generate title
        title = self._generate_title(evaluation, policy_version)

        # Create exception
        exception = Exception(
            evaluation_id=evaluation.id,
            fingerprint=fingerprint,
            severity=severity,
            title=title,
            context=context,
            options=options
        )

        self.db.add(exception)
        self.db.flush()  # Get exception ID

        # Create audit event
        audit_event = AuditEvent(
            event_type=AuditEventType.EXCEPTION_RAISED,
            aggregate_type="exception",
            aggregate_id=exception.id,
            event_data={
                "evaluation_id": str(evaluation.id),
                "severity": severity_str,
                "fingerprint": fingerprint,
                "title": title
            },
            actor="system"
        )

        self.db.add(audit_event)
        self.db.commit()

        # Log exception raised
        logger.exception_raised(
            exception_id=exception.id,
            evaluation_id=evaluation.id,
            severity=severity_str,
            fingerprint=fingerprint,
            title=title
        )

        return exception

    def _extract_key_dimensions(
        self,
        evaluation: Evaluation,
        policy_version: PolicyVersion
    ) -> Dict[str, Any]:
        """
        Extract key dimensions for fingerprint deduplication.

        Args:
            evaluation: Evaluation object
            policy_version: PolicyVersion object

        Returns:
            Dictionary of key dimensions
        """
        details = evaluation.details
        matched_signals = details.get("matched_signals", [])

        # For treasury position limits: use asset
        # For volatility: use asset
        # Generalized: use signal type and first matched signal's key fields

        if matched_signals:
            # Extract from first matched signal
            # In production, this would be more sophisticated
            return {
                "signal_types": [s["type"] for s in matched_signals]
            }

        return {"type": policy_version.rule_definition.get("type")}

    def _generate_context(
        self,
        evaluation: Evaluation,
        policy_version: PolicyVersion
    ) -> Dict[str, Any]:
        """
        Generate context for UI presentation.

        Context should be compact and focused on key facts.

        Args:
            evaluation: Evaluation object
            policy_version: PolicyVersion object

        Returns:
            Context dictionary
        """
        return {
            "policy_name": policy_version.policy.name,
            "evaluation_details": evaluation.details,
            "evaluation_time": evaluation.evaluated_at.isoformat(),
            "signal_count": len(evaluation.signal_ids)
        }

    def _generate_options(
        self,
        evaluation: Evaluation,
        policy_version: PolicyVersion
    ) -> List[Dict[str, Any]]:
        """
        Generate symmetric decision options.

        CRITICAL: All options MUST have equal visual weight.
        NO "recommended" field or ranking allowed.

        Args:
            evaluation: Evaluation object
            policy_version: PolicyVersion object

        Returns:
            List of option dictionaries

        Structure:
            [
                {
                    "id": "option_a",
                    "label": "Option A Label",
                    "description": "What this option means",
                    "implications": ["Implication 1", "Implication 2"]
                },
                ...
            ]
        """
        # For now, use generic options
        # In production, this would load from Treasury pack option templates
        rule_type = policy_version.rule_definition.get("type", "unknown")

        if rule_type == "threshold_breach":
            return [
                {
                    "id": "approve_temporary_increase",
                    "label": "Approve Temporary Increase",
                    "description": "Allow condition to persist for defined period",
                    "implications": [
                        "Increased risk exposure",
                        "Requires monitoring",
                        "May need board notification if critical"
                    ]
                },
                {
                    "id": "immediate_resolution",
                    "label": "Require Immediate Resolution",
                    "description": "Mandate corrective action to resolve condition",
                    "implications": [
                        "May incur operational costs",
                        "Reduces risk exposure",
                        "Could impact execution"
                    ]
                },
                {
                    "id": "escalate",
                    "label": "Escalate to Senior Leadership",
                    "description": "Elevate decision for higher-level review",
                    "implications": [
                        "Delays resolution",
                        "Higher-level accountability",
                        "Appropriate for critical severity"
                    ]
                }
            ]

        # Default options
        return [
            {
                "id": "approve",
                "label": "Approve",
                "description": "Accept current state",
                "implications": ["Accepts current risk profile"]
            },
            {
                "id": "reject",
                "label": "Reject",
                "description": "Require corrective action",
                "implications": ["Mandates resolution"]
            }
        ]

    def _generate_title(
        self,
        evaluation: Evaluation,
        policy_version: PolicyVersion
    ) -> str:
        """
        Generate human-readable exception title.

        Args:
            evaluation: Evaluation object
            policy_version: PolicyVersion object

        Returns:
            Title string (max 500 chars)
        """
        details = evaluation.details
        matched_signals = details.get("matched_signals", [])

        if matched_signals:
            signal_types = ", ".join([s["type"] for s in matched_signals])
            return f"{policy_version.policy.name}: {signal_types}"

        return f"{policy_version.policy.name}: Evaluation Failed"

    def _map_severity(self, severity_str: str) -> ExceptionSeverity:
        """
        Map string severity to enum.

        Args:
            severity_str: "critical" | "high" | "medium" | "low"

        Returns:
            ExceptionSeverity enum value
        """
        mapping = {
            "critical": ExceptionSeverity.CRITICAL,
            "high": ExceptionSeverity.HIGH,
            "medium": ExceptionSeverity.MEDIUM,
            "low": ExceptionSeverity.LOW
        }
        return mapping.get(severity_str, ExceptionSeverity.MEDIUM)
