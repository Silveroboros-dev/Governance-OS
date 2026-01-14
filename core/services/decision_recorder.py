"""
Decision Recorder Service.

Records immutable decisions for exceptions.
Once recorded, decisions CANNOT be modified.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.models import Decision, DecisionType, Exception, ExceptionStatus, AuditEvent, AuditEventType
from core.logging import get_logger

logger = get_logger(__name__)


class DecisionRecorder:
    """
    Decision recording service.

    CRITICAL: Decisions are IMMUTABLE.
    - No UPDATE operations allowed
    - Enforced at application level
    """

    def __init__(self, db: Session):
        """
        Initialize decision recorder.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def record_decision(
        self,
        exception_id: UUID,
        chosen_option_id: str,
        rationale: str,
        decided_by: str,
        assumptions: Optional[str] = None,
        is_hard_override: bool = False,
        approved_by: Optional[str] = None,
        approval_notes: Optional[str] = None
    ) -> Decision:
        """
        Record immutable decision.

        Validates:
        1. Exception exists and is open
        2. Chosen option is valid (exists in exception.options)
        3. Rationale is provided (required!)
        4. Hard overrides have approval

        Side effects:
        1. Creates Decision record
        2. Marks Exception as resolved
        3. Creates audit event
        4. Triggers async evidence pack generation (future)

        Args:
            exception_id: UUID of the exception
            chosen_option_id: ID of chosen option from exception.options
            rationale: Human explanation of decision (REQUIRED)
            decided_by: User/role who made the decision
            assumptions: Explicit assumptions (optional)
            is_hard_override: True if this overrides policy recommendation
            approved_by: Approver username (required for hard overrides)
            approval_notes: Approver's justification (optional)

        Returns:
            Decision object

        Raises:
            ValueError: If validation fails
            IntegrityError: If decision already exists for this exception

        Example:
            >>> recorder = DecisionRecorder(db)
            >>> decision = recorder.record_decision(
            ...     exception_id=exc_id,
            ...     chosen_option_id="approve_temporary_increase",
            ...     rationale="Market conditions justify temporary position increase",
            ...     decided_by="treasury_manager",
            ...     assumptions="Volatility will normalize within 24 hours"
            ... )
            >>> decision.id
            UUID('...')
        """
        # Step 1: Validate exception exists and is open
        exception = self.db.query(Exception).filter(Exception.id == exception_id).first()

        if not exception:
            logger.decision_validation_failed(
                exception_id=exception_id,
                error=f"Exception {exception_id} not found"
            )
            raise ValueError(f"Exception {exception_id} not found")

        if exception.status != ExceptionStatus.OPEN:
            logger.decision_validation_failed(
                exception_id=exception_id,
                error=f"Exception not open (status: {exception.status})"
            )
            raise ValueError(f"Exception {exception_id} is not open (status: {exception.status})")

        # Step 2: Validate chosen option
        valid_option_ids = [opt["id"] for opt in exception.options]

        if chosen_option_id not in valid_option_ids:
            error_msg = f"Invalid option '{chosen_option_id}'. Valid options: {', '.join(valid_option_ids)}"
            logger.decision_validation_failed(
                exception_id=exception_id,
                error=error_msg
            )
            raise ValueError(error_msg)

        # Step 3: Validate rationale
        if not rationale or not rationale.strip():
            logger.decision_validation_failed(
                exception_id=exception_id,
                error="Rationale is required and cannot be empty"
            )
            raise ValueError("Rationale is required and cannot be empty")

        # Step 4: Validate hard override approval
        if is_hard_override and not approved_by:
            logger.decision_validation_failed(
                exception_id=exception_id,
                error="Hard overrides require approved_by"
            )
            raise ValueError("Hard overrides require approved_by")

        # Step 5: Create decision record (IMMUTABLE)
        decision = Decision(
            exception_id=exception_id,
            chosen_option_id=chosen_option_id,
            rationale=rationale.strip(),
            assumptions=assumptions.strip() if assumptions else None,
            decided_by=decided_by,
            # Hard override fields
            decision_type=DecisionType.HARD_OVERRIDE if is_hard_override else DecisionType.STANDARD,
            is_hard_override=is_hard_override,
            approved_by=approved_by if is_hard_override else None,
            approved_at=datetime.utcnow() if is_hard_override else None,
            approval_notes=approval_notes if is_hard_override else None
        )

        self.db.add(decision)
        self.db.flush()  # Flush to generate decision.id before using it in audit event

        # Step 6: Mark exception as resolved
        exception.status = ExceptionStatus.RESOLVED
        exception.resolved_at = decision.decided_at

        # Step 7: Create audit event
        event_data = {
            "exception_id": str(exception_id),
            "chosen_option_id": chosen_option_id,
            "decided_by": decided_by,
            "rationale_length": len(rationale),
            "is_hard_override": is_hard_override
        }
        if is_hard_override:
            event_data["approved_by"] = approved_by

        audit_event = AuditEvent(
            event_type=AuditEventType.DECISION_RECORDED,
            aggregate_type="decision",
            aggregate_id=decision.id,
            event_data=event_data,
            actor=decided_by
        )

        self.db.add(audit_event)

        # Step 8: Commit (make immutable!)
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.decision_validation_failed(
                exception_id=exception_id,
                error=f"Database integrity error: {str(e)}"
            )
            raise ValueError(f"Failed to record decision: {str(e)}")

        # Log decision recorded
        logger.decision_recorded(
            decision_id=decision.id,
            exception_id=exception_id,
            chosen_option_id=chosen_option_id,
            decided_by=decided_by,
            is_hard_override=is_hard_override
        )

        # Step 9: Trigger evidence pack generation (would be async in production)
        # For Sprint 1, we'll generate synchronously
        # In Sprint 2+, this would be a background task

        return decision

    def get_decision(self, decision_id: UUID) -> Optional[Decision]:
        """
        Get decision by ID.

        Args:
            decision_id: UUID of the decision

        Returns:
            Decision object or None
        """
        return self.db.query(Decision).filter(Decision.id == decision_id).first()

    def get_decisions_for_exception(self, exception_id: UUID) -> list[Decision]:
        """
        Get all decisions for an exception.

        Typically there should be only one, but this handles edge cases.

        Args:
            exception_id: UUID of the exception

        Returns:
            List of Decision objects
        """
        return (
            self.db.query(Decision)
            .filter(Decision.exception_id == exception_id)
            .order_by(Decision.decided_at)
            .all()
        )
