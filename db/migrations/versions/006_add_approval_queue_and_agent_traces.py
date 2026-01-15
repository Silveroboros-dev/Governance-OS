"""add_approval_queue_and_agent_traces

Revision ID: 006
Revises: 005
Create Date: 2026-01-15 00:00:00.000000

Sprint 3: Foundation tables for agentic coprocessor
- approval_queue: Gated write operations requiring human review
- agent_traces: Observability for agent executions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005_add_immutability_triggers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types for Sprint 3
    op.execute("""
        CREATE TYPE approval_action_type AS ENUM (
            'signal', 'policy_draft', 'decision', 'dismiss', 'context'
        );
        CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'rejected');
        CREATE TYPE agent_type AS ENUM ('intake', 'narrative', 'policy_draft');
        CREATE TYPE agent_trace_status AS ENUM ('running', 'completed', 'failed');
    """)

    # Create approval_queue table
    op.create_table(
        'approval_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('action_type', postgresql.ENUM(
            'signal', 'policy_draft', 'decision', 'dismiss', 'context',
            name='approval_action_type', create_type=False
        ), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('proposed_by', sa.String(100), nullable=False),  # agent identifier
        sa.Column('proposed_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('status', postgresql.ENUM(
            'pending', 'approved', 'rejected',
            name='approval_status', create_type=False
        ), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text, nullable=True),
        sa.Column('result_id', postgresql.UUID(as_uuid=True), nullable=True),  # ID of created entity
        # For linking to agent trace
        sa.Column('trace_id', postgresql.UUID(as_uuid=True), nullable=True),
        # Additional context for display
        sa.Column('summary', sa.String(500), nullable=True),
        sa.Column('confidence', sa.Float, nullable=True),  # 0.0-1.0 for signals
    )
    op.create_index('idx_approval_queue_status', 'approval_queue', ['status'])
    op.create_index('idx_approval_queue_action_type', 'approval_queue', ['action_type'])
    op.create_index('idx_approval_queue_proposed_at', 'approval_queue', ['proposed_at'])
    op.create_index('idx_approval_queue_trace', 'approval_queue', ['trace_id'])

    # Create agent_traces table
    op.create_table(
        'agent_traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_type', postgresql.ENUM(
            'intake', 'narrative', 'policy_draft',
            name='agent_type', create_type=False
        ), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM(
            'running', 'completed', 'failed',
            name='agent_trace_status', create_type=False
        ), nullable=False, server_default='running'),
        sa.Column('input_summary', postgresql.JSONB, nullable=True),
        sa.Column('output_summary', postgresql.JSONB, nullable=True),
        sa.Column('tool_calls', postgresql.ARRAY(postgresql.JSONB), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        # Additional metadata
        sa.Column('pack', sa.String(100), nullable=True),  # treasury/wealth
        sa.Column('document_source', sa.String(500), nullable=True),  # for intake agent
        sa.Column('total_duration_ms', sa.Integer, nullable=True),
    )
    op.create_index('idx_agent_traces_session', 'agent_traces', ['session_id'])
    op.create_index('idx_agent_traces_status', 'agent_traces', ['status'])
    op.create_index('idx_agent_traces_agent_type', 'agent_traces', ['agent_type'])
    op.create_index('idx_agent_traces_started_at', 'agent_traces', ['started_at'])

    # Add foreign key from approval_queue to agent_traces
    op.create_foreign_key(
        'fk_approval_queue_trace',
        'approval_queue', 'agent_traces',
        ['trace_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add new audit event types for Sprint 3
    op.execute("""
        ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'approval_proposed';
        ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'approval_approved';
        ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'approval_rejected';
        ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'agent_execution_started';
        ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'agent_execution_completed';
        ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'agent_execution_failed';
    """)


def downgrade() -> None:
    # Drop foreign key first
    op.drop_constraint('fk_approval_queue_trace', 'approval_queue', type_='foreignkey')

    # Drop tables
    op.drop_table('approval_queue')
    op.drop_table('agent_traces')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS approval_action_type")
    op.execute("DROP TYPE IF EXISTS approval_status")
    op.execute("DROP TYPE IF EXISTS agent_type")
    op.execute("DROP TYPE IF EXISTS agent_trace_status")

    # Note: Cannot easily remove enum values in PostgreSQL
    # The added audit_event_type values will remain
