"""Add approval rules for hard overrides.

Revision ID: 004_approval_rules
Revises: 003_eval_unique
Create Date: 2025-01-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_approval_rules'
down_revision = '003_eval_unique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_role enum
    user_role_enum = postgresql.ENUM(
        'viewer', 'decider', 'approver', 'admin',
        name='user_role',
        create_type=False
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # Create decision_type enum
    decision_type_enum = postgresql.ENUM(
        'standard', 'hard_override',
        name='decision_type',
        create_type=False
    )
    decision_type_enum.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('role', postgresql.ENUM('viewer', 'decider', 'approver', 'admin', name='user_role', create_type=False), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Add new columns to decisions table
    op.add_column('decisions', sa.Column(
        'decision_type',
        postgresql.ENUM('standard', 'hard_override', name='decision_type', create_type=False),
        nullable=True  # Nullable initially for existing data
    ))
    op.add_column('decisions', sa.Column('is_hard_override', sa.Boolean(), nullable=True))
    op.add_column('decisions', sa.Column('approved_by', sa.String(255), nullable=True))
    op.add_column('decisions', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('decisions', sa.Column('approval_notes', sa.Text(), nullable=True))

    # Set defaults for existing data
    op.execute("UPDATE decisions SET decision_type = 'standard', is_hard_override = false WHERE decision_type IS NULL")

    # Make columns non-nullable after backfill
    op.alter_column('decisions', 'decision_type', nullable=False)
    op.alter_column('decisions', 'is_hard_override', nullable=False)

    # Add check constraint for hard override approval requirement
    op.create_check_constraint(
        'ck_hard_override_requires_approval',
        'decisions',
        "(is_hard_override = false) OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)"
    )


def downgrade() -> None:
    op.drop_constraint('ck_hard_override_requires_approval', 'decisions', type_='check')
    op.drop_column('decisions', 'approval_notes')
    op.drop_column('decisions', 'approved_at')
    op.drop_column('decisions', 'approved_by')
    op.drop_column('decisions', 'is_hard_override')
    op.drop_column('decisions', 'decision_type')
    op.drop_table('users')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS decision_type")
