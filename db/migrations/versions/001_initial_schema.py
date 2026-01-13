"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-01-13 23:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE policy_status AS ENUM ('draft', 'active', 'archived');
        CREATE TYPE evaluation_result AS ENUM ('pass', 'fail', 'exception_raised');
        CREATE TYPE exception_severity AS ENUM ('low', 'medium', 'high', 'critical');
        CREATE TYPE exception_status AS ENUM ('open', 'resolved', 'dismissed');
        CREATE TYPE signal_reliability AS ENUM ('low', 'medium', 'high', 'verified');
        CREATE TYPE audit_event_type AS ENUM (
            'policy_created', 'policy_version_created', 'policy_activated',
            'signal_received', 'evaluation_executed', 'exception_raised',
            'decision_recorded', 'evidence_pack_generated'
        );
    """)

    # Create policies table
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('pack', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('idx_policies_pack', 'policies', ['pack'])

    # Create policy_versions table
    op.create_table(
        'policy_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('status', postgresql.ENUM('draft', 'active', 'archived', name='policy_status', create_type=False), nullable=False),
        sa.Column('rule_definition', postgresql.JSONB, nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('changelog', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE')
    )
    op.create_unique_constraint('uq_policy_version', 'policy_versions', ['policy_id', 'version_number'])
    op.create_index('idx_policy_versions_valid', 'policy_versions', ['valid_from', 'valid_to'])

    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pack', sa.String(100), nullable=False),
        sa.Column('signal_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('source', sa.String(255), nullable=False),
        sa.Column('reliability', postgresql.ENUM('low', 'medium', 'high', 'verified', name='signal_reliability', create_type=False), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True)
    )
    op.create_index('idx_signals_pack_type', 'signals', ['pack', 'signal_type'])
    op.create_index('idx_signals_observed_at', 'signals', ['observed_at'])

    # Create evaluations table
    op.create_table(
        'evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('result', postgresql.ENUM('pass', 'fail', 'exception_raised', name='evaluation_result', create_type=False), nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=False),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['policy_version_id'], ['policy_versions.id'])
    )
    op.create_index('idx_evaluations_input_hash', 'evaluations', ['input_hash'])

    # Create exceptions table
    op.create_table(
        'exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('evaluation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('severity', postgresql.ENUM('low', 'medium', 'high', 'critical', name='exception_severity', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('open', 'resolved', 'dismissed', name='exception_status', create_type=False), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('context', postgresql.JSONB, nullable=False),
        sa.Column('options', postgresql.JSONB, nullable=False),
        sa.Column('raised_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'])
    )
    op.create_unique_constraint('uq_exception_fingerprint_resolved', 'exceptions', ['fingerprint', 'resolved_at'])
    op.create_index('idx_exceptions_status', 'exceptions', ['status'])

    # Create decisions table
    op.create_table(
        'decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('exception_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chosen_option_id', sa.String(100), nullable=False),
        sa.Column('rationale', sa.Text, nullable=False),
        sa.Column('assumptions', sa.Text, nullable=True),
        sa.Column('decided_by', sa.String(255), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_pack_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['exception_id'], ['exceptions.id'])
    )
    op.create_index('idx_decisions_decided_at', 'decisions', ['decided_at'])

    # Create evidence_packs table
    op.create_table(
        'evidence_packs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('decision_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evidence', postgresql.JSONB, nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['decision_id'], ['decisions.id'])
    )
    op.create_unique_constraint('uq_evidence_pack_decision', 'evidence_packs', ['decision_id'])

    # Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', postgresql.ENUM(
            'policy_created', 'policy_version_created', 'policy_activated',
            'signal_received', 'evaluation_executed', 'exception_raised',
            'decision_recorded', 'evidence_pack_generated',
            name='audit_event_type', create_type=False
        ), nullable=False),
        sa.Column('aggregate_type', sa.String(100), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_data', postgresql.JSONB, nullable=False),
        sa.Column('actor', sa.String(255), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('idx_audit_events_aggregate', 'audit_events', ['aggregate_id'])
    op.create_index('idx_audit_events_occurred_at', 'audit_events', ['occurred_at'])


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('evidence_packs')
    op.drop_table('decisions')
    op.drop_table('exceptions')
    op.drop_table('evaluations')
    op.drop_table('signals')
    op.drop_table('policy_versions')
    op.drop_table('policies')

    op.execute("DROP TYPE IF EXISTS audit_event_type")
    op.execute("DROP TYPE IF EXISTS signal_reliability")
    op.execute("DROP TYPE IF EXISTS exception_status")
    op.execute("DROP TYPE IF EXISTS exception_severity")
    op.execute("DROP TYPE IF EXISTS evaluation_result")
    op.execute("DROP TYPE IF EXISTS policy_status")
