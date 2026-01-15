"""
Sprint 3: Approval Queue Tests

Tests for the approval queue model and API endpoints.
All agent writes must go through the approval queue.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from core.models.approval import ApprovalQueue, ApprovalActionType, ApprovalStatus
from core.models.trace import AgentTrace, AgentType, AgentTraceStatus


class TestApprovalQueueModel:
    """Test ApprovalQueue model behavior."""

    def test_create_signal_approval(self, db_session):
        """Test creating a signal proposal approval."""
        approval = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={
                "pack": "treasury",
                "signal_type": "position_limit_breach",
                "payload": {"asset": "BTC", "current_position": 120, "limit": 100},
                "source": "email",
            },
            proposed_by="intake_agent",
            summary="Position limit breach for BTC (120 > 100)",
            confidence=0.85,
        )
        db_session.add(approval)
        db_session.commit()

        assert approval.id is not None
        assert approval.status == ApprovalStatus.PENDING
        assert approval.action_type == ApprovalActionType.SIGNAL
        assert approval.proposed_at is not None
        assert approval.reviewed_at is None
        assert approval.reviewed_by is None

    def test_create_policy_draft_approval(self, db_session):
        """Test creating a policy draft proposal approval."""
        approval = ApprovalQueue(
            action_type=ApprovalActionType.POLICY_DRAFT,
            payload={
                "pack": "treasury",
                "name": "Position Limit Policy",
                "description": "Monitors position limit breaches",
                "rules": [
                    {"id": "rule_1", "condition": "position > limit", "action": "raise_exception"}
                ],
            },
            proposed_by="policy_draft_agent",
            summary="New policy: Position Limit Policy",
        )
        db_session.add(approval)
        db_session.commit()

        assert approval.id is not None
        assert approval.status == ApprovalStatus.PENDING
        assert approval.action_type == ApprovalActionType.POLICY_DRAFT
        assert approval.confidence is None  # Not applicable for policy drafts

    def test_approve_approval(self, db_session):
        """Test approving an approval request."""
        approval = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"pack": "treasury", "signal_type": "test"},
            proposed_by="test_agent",
        )
        db_session.add(approval)
        db_session.commit()

        # Approve
        result_id = uuid4()
        approval.approve(
            reviewed_by="test_user",
            result_id=result_id,
            notes="Looks good, approved."
        )
        db_session.commit()

        assert approval.status == ApprovalStatus.APPROVED
        assert approval.reviewed_by == "test_user"
        assert approval.reviewed_at is not None
        assert approval.result_id == result_id
        assert approval.review_notes == "Looks good, approved."

    def test_reject_approval(self, db_session):
        """Test rejecting an approval request."""
        approval = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"pack": "treasury", "signal_type": "test"},
            proposed_by="test_agent",
        )
        db_session.add(approval)
        db_session.commit()

        # Reject
        approval.reject(
            reviewed_by="test_user",
            notes="Invalid signal type."
        )
        db_session.commit()

        assert approval.status == ApprovalStatus.REJECTED
        assert approval.reviewed_by == "test_user"
        assert approval.reviewed_at is not None
        assert approval.result_id is None
        assert approval.review_notes == "Invalid signal type."

    def test_approval_with_trace_link(self, db_session):
        """Test linking approval to agent trace."""
        # Create trace first
        trace = AgentTrace(
            agent_type=AgentType.INTAKE,
            session_id=uuid4(),
            pack="treasury",
        )
        db_session.add(trace)
        db_session.flush()

        # Create approval linked to trace
        approval = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"pack": "treasury", "signal_type": "test"},
            proposed_by="intake_agent",
            trace_id=trace.id,
        )
        db_session.add(approval)
        db_session.commit()

        assert approval.trace_id == trace.id
        assert approval.trace == trace
        assert approval in trace.approvals

    def test_query_pending_approvals(self, db_session):
        """Test querying pending approvals."""
        # Create mix of approvals
        for i in range(3):
            db_session.add(ApprovalQueue(
                action_type=ApprovalActionType.SIGNAL,
                payload={"test": i},
                proposed_by="test_agent",
                status=ApprovalStatus.PENDING,
            ))

        db_session.add(ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"test": "approved"},
            proposed_by="test_agent",
            status=ApprovalStatus.APPROVED,
            reviewed_by="user",
            reviewed_at=datetime.utcnow(),
        ))
        db_session.commit()

        pending = db_session.query(ApprovalQueue).filter(
            ApprovalQueue.status == ApprovalStatus.PENDING
        ).all()

        assert len(pending) == 3

    def test_query_by_action_type(self, db_session):
        """Test querying approvals by action type."""
        db_session.add(ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"type": "signal"},
            proposed_by="test_agent",
        ))
        db_session.add(ApprovalQueue(
            action_type=ApprovalActionType.POLICY_DRAFT,
            payload={"type": "policy"},
            proposed_by="test_agent",
        ))
        db_session.add(ApprovalQueue(
            action_type=ApprovalActionType.DISMISS,
            payload={"type": "dismiss"},
            proposed_by="test_agent",
        ))
        db_session.commit()

        signals = db_session.query(ApprovalQueue).filter(
            ApprovalQueue.action_type == ApprovalActionType.SIGNAL
        ).all()
        assert len(signals) == 1

        policies = db_session.query(ApprovalQueue).filter(
            ApprovalQueue.action_type == ApprovalActionType.POLICY_DRAFT
        ).all()
        assert len(policies) == 1


class TestApprovalQueueValidation:
    """Test approval queue validation constraints."""

    def test_action_type_required(self, db_session):
        """Test that action_type is required."""
        with pytest.raises(Exception):
            approval = ApprovalQueue(
                payload={"test": "data"},
                proposed_by="test_agent",
            )
            db_session.add(approval)
            db_session.commit()

    def test_payload_required(self, db_session):
        """Test that payload is required."""
        with pytest.raises(Exception):
            approval = ApprovalQueue(
                action_type=ApprovalActionType.SIGNAL,
                proposed_by="test_agent",
            )
            db_session.add(approval)
            db_session.commit()

    def test_proposed_by_required(self, db_session):
        """Test that proposed_by is required."""
        with pytest.raises(Exception):
            approval = ApprovalQueue(
                action_type=ApprovalActionType.SIGNAL,
                payload={"test": "data"},
            )
            db_session.add(approval)
            db_session.commit()


class TestApprovalQueueEdgeCases:
    """Test edge cases for approval queue."""

    def test_approve_already_approved(self, db_session):
        """Test approving an already approved request."""
        approval = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={"test": "data"},
            proposed_by="test_agent",
        )
        db_session.add(approval)
        db_session.commit()

        # First approve
        approval.approve("user_1", notes="First approval")
        db_session.commit()
        first_reviewed_at = approval.reviewed_at

        # Second approve (should overwrite)
        approval.approve("user_2", notes="Second approval")
        db_session.commit()

        assert approval.reviewed_by == "user_2"
        assert approval.review_notes == "Second approval"
        # reviewed_at gets updated
        assert approval.reviewed_at >= first_reviewed_at

    def test_large_payload(self, db_session):
        """Test handling of large payloads."""
        large_content = "x" * 100000  # 100KB of data
        approval = ApprovalQueue(
            action_type=ApprovalActionType.SIGNAL,
            payload={
                "large_field": large_content,
                "nested": {"more": large_content[:1000]},
            },
            proposed_by="test_agent",
        )
        db_session.add(approval)
        db_session.commit()

        # Retrieve and verify
        loaded = db_session.get(ApprovalQueue, approval.id)
        assert len(loaded.payload["large_field"]) == 100000

    def test_complex_payload_structure(self, db_session):
        """Test complex nested payload structures."""
        approval = ApprovalQueue(
            action_type=ApprovalActionType.POLICY_DRAFT,
            payload={
                "pack": "treasury",
                "rules": [
                    {
                        "id": "rule_1",
                        "conditions": [
                            {"field": "position", "operator": ">", "value": 100},
                            {"field": "duration_hours", "operator": ">=", "value": 2},
                        ],
                        "actions": [
                            {"type": "raise_exception", "severity": "high"},
                            {"type": "notify", "channels": ["email", "slack"]},
                        ],
                    }
                ],
                "test_scenarios": [
                    {"signals": [{"type": "test", "value": 1}], "expected": "pass"},
                    {"signals": [{"type": "test", "value": 200}], "expected": "exception"},
                ],
            },
            proposed_by="policy_draft_agent",
        )
        db_session.add(approval)
        db_session.commit()

        loaded = db_session.get(ApprovalQueue, approval.id)
        assert len(loaded.payload["rules"]) == 1
        assert len(loaded.payload["rules"][0]["conditions"]) == 2
