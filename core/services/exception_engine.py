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

# Import pack option templates
from packs.treasury.option_templates import TREASURY_OPTION_TEMPLATES
from packs.wealth.option_templates import WEALTH_OPTION_TEMPLATES

# Import pack-specific fingerprint extractors
from packs.treasury.fingerprint_extractors import (
    extract_key_dimensions as treasury_extract_key_dimensions
)
from packs.wealth.fingerprint_extractors import (
    extract_key_dimensions as wealth_extract_key_dimensions
)

logger = get_logger(__name__)

# Registry of pack option templates
PACK_OPTION_TEMPLATES = {
    "treasury": TREASURY_OPTION_TEMPLATES,
    "wealth": WEALTH_OPTION_TEMPLATES,
}

# Registry of pack fingerprint extractors
PACK_FINGERPRINT_EXTRACTORS = {
    "treasury": treasury_extract_key_dimensions,
    "wealth": wealth_extract_key_dimensions,
}


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

        Uses pack-specific extractors to identify the correct key dimensions
        based on signal type. This ensures proper deduplication:
        - Treasury: asset, counterparty, currency_pair, account, etc.
        - Wealth: client_id, portfolio_id, security_id, etc.

        Args:
            evaluation: Evaluation object
            policy_version: PolicyVersion object

        Returns:
            Dictionary of key dimensions
        """
        details = evaluation.details
        matched_signals = details.get("matched_signals", [])

        # Get pack-specific extractor
        pack = policy_version.policy.pack
        extractor = PACK_FINGERPRINT_EXTRACTORS.get(pack)

        if matched_signals and extractor:
            # Use pack-specific extractor for the first matched signal
            first_signal = matched_signals[0]
            signal_type = first_signal.get("type")
            payload = first_signal.get("payload", {})

            if signal_type:
                key_dims = extractor(signal_type, payload)
                # Always include signal type for clarity
                key_dims["signal_type"] = signal_type
                return key_dims

        # Fallback: use generic dimensions
        if matched_signals:
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
        Generate symmetric decision options from pack templates.

        CRITICAL: All options MUST have equal visual weight.
        NO "recommended" field or ranking allowed.

        Options are loaded from pack-specific templates based on:
        1. Pack name (treasury, wealth)
        2. Signal type or exception type

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
        # Get pack from policy
        pack = policy_version.policy.pack

        # Get pack's option templates
        pack_templates = PACK_OPTION_TEMPLATES.get(pack, {})

        # Try to find options based on matched signal types
        details = evaluation.details
        matched_signals = details.get("matched_signals", [])

        if matched_signals:
            # Use the first matched signal type to find options
            for signal in matched_signals:
                signal_type = signal.get("type")
                if signal_type and signal_type in pack_templates:
                    options = pack_templates[signal_type]
                    # Ensure each option has an id (some templates may be missing it)
                    return self._ensure_option_ids(options, signal_type)

        # Try rule type as fallback
        rule_type = policy_version.rule_definition.get("type", "unknown")
        if rule_type in pack_templates:
            options = pack_templates[rule_type]
            return self._ensure_option_ids(options, rule_type)

        # Default options if no template found
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
            },
            {
                "id": "escalate",
                "label": "Escalate",
                "description": "Refer to senior oversight",
                "implications": ["Delays decision", "Higher-level review"]
            }
        ]

    def _ensure_option_ids(
        self,
        options: List[Dict[str, Any]],
        prefix: str
    ) -> List[Dict[str, Any]]:
        """
        Ensure all options have unique IDs.

        Some pack templates may not have IDs - generate them from labels.

        Args:
            options: List of option dictionaries
            prefix: Prefix for generated IDs

        Returns:
            Options with guaranteed IDs
        """
        result = []
        for i, opt in enumerate(options):
            option = opt.copy()
            if "id" not in option:
                # Generate ID from label or index
                label = option.get("label", f"option_{i}")
                option["id"] = label.lower().replace(" ", "_").replace("-", "_")
            result.append(option)
        return result

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
