"""
Structured Logging Module for Governance OS.

Provides JSON-formatted structured logging for observability.
Key events: ingestion, evaluation, exception creation, decision confirmation.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from core.config import settings


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    All logs are emitted as single-line JSON objects for easy parsing
    by log aggregation tools (CloudWatch, Datadog, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """
    Structured logger wrapper with domain-specific methods.

    Provides type-safe logging for governance kernel events.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(
        self,
        level: int,
        message: str,
        **kwargs: Any
    ) -> None:
        """Internal log method with extra fields."""
        extra = {"extra_fields": kwargs}
        self.logger.log(level, message, extra=extra)

    # ===== Ingestion Events =====

    def ingestion_started(
        self,
        source_file: str,
        pack: str,
        batch_id: str
    ) -> None:
        """Log CSV ingestion started."""
        self._log(
            logging.INFO,
            "Ingestion started",
            event="ingestion.started",
            source_file=source_file,
            pack=pack,
            batch_id=batch_id
        )

    def ingestion_completed(
        self,
        batch_id: str,
        signals_created: int,
        signals_deduplicated: int,
        parse_errors: int,
        duration_ms: Optional[float] = None
    ) -> None:
        """Log CSV ingestion completed."""
        self._log(
            logging.INFO,
            f"Ingestion completed: {signals_created} created, {signals_deduplicated} deduplicated",
            event="ingestion.completed",
            batch_id=batch_id,
            signals_created=signals_created,
            signals_deduplicated=signals_deduplicated,
            parse_errors=parse_errors,
            duration_ms=duration_ms
        )

    def ingestion_failed(
        self,
        batch_id: str,
        error: str,
        row_number: Optional[int] = None
    ) -> None:
        """Log CSV ingestion failure."""
        self._log(
            logging.ERROR,
            f"Ingestion failed: {error}",
            event="ingestion.failed",
            batch_id=batch_id,
            error=error,
            row_number=row_number
        )

    def ingestion_row_error(
        self,
        batch_id: str,
        row_number: int,
        error: str
    ) -> None:
        """Log single row parse error during ingestion."""
        self._log(
            logging.WARNING,
            f"Row parse error at row {row_number}: {error}",
            event="ingestion.row_error",
            batch_id=batch_id,
            row_number=row_number,
            error=error
        )

    # ===== Evaluation Events =====

    def evaluation_started(
        self,
        policy_version_id: UUID,
        signal_count: int,
        replay_namespace: str = "production"
    ) -> None:
        """Log policy evaluation started."""
        self._log(
            logging.INFO,
            f"Evaluation started for policy version {policy_version_id}",
            event="evaluation.started",
            policy_version_id=str(policy_version_id),
            signal_count=signal_count,
            replay_namespace=replay_namespace
        )

    def evaluation_completed(
        self,
        evaluation_id: UUID,
        policy_version_id: UUID,
        result: str,
        input_hash: str,
        signal_count: int,
        is_cached: bool = False
    ) -> None:
        """Log policy evaluation completed."""
        self._log(
            logging.INFO,
            f"Evaluation completed: {result}",
            event="evaluation.completed",
            evaluation_id=str(evaluation_id),
            policy_version_id=str(policy_version_id),
            result=result,
            input_hash=input_hash,
            signal_count=signal_count,
            is_cached=is_cached
        )

    def evaluation_cache_hit(
        self,
        input_hash: str,
        evaluation_id: UUID
    ) -> None:
        """Log evaluation cache hit (idempotency)."""
        self._log(
            logging.DEBUG,
            f"Evaluation cache hit for hash {input_hash[:16]}...",
            event="evaluation.cache_hit",
            input_hash=input_hash,
            evaluation_id=str(evaluation_id)
        )

    # ===== Exception Events =====

    def exception_raised(
        self,
        exception_id: UUID,
        evaluation_id: UUID,
        severity: str,
        fingerprint: str,
        title: str
    ) -> None:
        """Log exception raised."""
        self._log(
            logging.WARNING,
            f"Exception raised: {title} (severity={severity})",
            event="exception.raised",
            exception_id=str(exception_id),
            evaluation_id=str(evaluation_id),
            severity=severity,
            fingerprint=fingerprint,
            title=title
        )

    def exception_deduplicated(
        self,
        fingerprint: str,
        existing_exception_id: UUID
    ) -> None:
        """Log exception deduplicated (not created due to existing open exception)."""
        self._log(
            logging.INFO,
            f"Exception deduplicated (fingerprint={fingerprint[:16]}...)",
            event="exception.deduplicated",
            fingerprint=fingerprint,
            existing_exception_id=str(existing_exception_id)
        )

    def exception_not_needed(
        self,
        evaluation_id: UUID,
        result: str
    ) -> None:
        """Log that no exception was needed (evaluation passed)."""
        self._log(
            logging.DEBUG,
            f"No exception needed (result={result})",
            event="exception.not_needed",
            evaluation_id=str(evaluation_id),
            result=result
        )

    # ===== Decision Events =====

    def decision_recorded(
        self,
        decision_id: UUID,
        exception_id: UUID,
        chosen_option_id: str,
        decided_by: str,
        is_hard_override: bool = False
    ) -> None:
        """Log decision recorded."""
        level = logging.WARNING if is_hard_override else logging.INFO
        self._log(
            level,
            f"Decision recorded: {chosen_option_id} by {decided_by}" +
            (" [HARD OVERRIDE]" if is_hard_override else ""),
            event="decision.recorded",
            decision_id=str(decision_id),
            exception_id=str(exception_id),
            chosen_option_id=chosen_option_id,
            decided_by=decided_by,
            is_hard_override=is_hard_override
        )

    def decision_validation_failed(
        self,
        exception_id: UUID,
        error: str
    ) -> None:
        """Log decision validation failure."""
        self._log(
            logging.ERROR,
            f"Decision validation failed: {error}",
            event="decision.validation_failed",
            exception_id=str(exception_id),
            error=error
        )

    # ===== Policy Events =====

    def policy_activated(
        self,
        policy_id: UUID,
        version_id: UUID,
        pack: str
    ) -> None:
        """Log policy version activated."""
        self._log(
            logging.INFO,
            f"Policy activated: {policy_id}",
            event="policy.activated",
            policy_id=str(policy_id),
            version_id=str(version_id),
            pack=pack
        )

    def policy_publish_failed(
        self,
        policy_id: UUID,
        error: str
    ) -> None:
        """Log policy publish failure."""
        self._log(
            logging.ERROR,
            f"Policy publish failed: {error}",
            event="policy.publish_failed",
            policy_id=str(policy_id),
            error=error
        )

    # ===== Evidence Events =====

    def evidence_pack_generated(
        self,
        evidence_pack_id: UUID,
        decision_id: UUID,
        duration_ms: Optional[float] = None
    ) -> None:
        """Log evidence pack generated."""
        self._log(
            logging.INFO,
            f"Evidence pack generated for decision {decision_id}",
            event="evidence.generated",
            evidence_pack_id=str(evidence_pack_id),
            decision_id=str(decision_id),
            duration_ms=duration_ms
        )


def setup_logging() -> None:
    """
    Configure application-wide logging.

    Should be called once at application startup.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    root_logger.handlers = []

    # Add JSON handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Set levels for noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.evaluation_completed(eval_id, policy_id, "fail", hash, 5)
    """
    return StructuredLogger(name)
