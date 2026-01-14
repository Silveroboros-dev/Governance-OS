"""Add content_hash column to signals for idempotency.

Revision ID: 002_add_signal_content_hash
Revises: add_inconclusive_enum_value
Create Date: 2025-01-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_signal_content_hash'
down_revision = 'add_inconclusive_enum_value'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add content_hash column (nullable initially for existing data)
    op.add_column(
        'signals',
        sa.Column('content_hash', sa.String(64), nullable=True)
    )

    # Create index for fast lookups
    op.create_index(
        'idx_signals_content_hash',
        'signals',
        ['content_hash']
    )

    # Create unique constraint (allows NULL for legacy signals)
    op.create_unique_constraint(
        'uq_signal_content_hash',
        'signals',
        ['content_hash']
    )


def downgrade() -> None:
    op.drop_constraint('uq_signal_content_hash', 'signals', type_='unique')
    op.drop_index('idx_signals_content_hash', table_name='signals')
    op.drop_column('signals', 'content_hash')
