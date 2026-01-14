"""Add unique constraint to evaluations for idempotency.

Revision ID: 003_add_evaluation_unique_constraint
Revises: 002_add_signal_content_hash
Create Date: 2025-01-14
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '003_add_evaluation_unique_constraint'
down_revision = '002_add_signal_content_hash'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint on (input_hash, replay_namespace)
    # This ensures same inputs in same namespace cannot create duplicate evaluations
    op.create_unique_constraint(
        'uq_evaluation_input_namespace',
        'evaluations',
        ['input_hash', 'replay_namespace']
    )


def downgrade() -> None:
    op.drop_constraint('uq_evaluation_input_namespace', 'evaluations', type_='unique')
