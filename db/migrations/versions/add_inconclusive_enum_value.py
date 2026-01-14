"""Add inconclusive to evaluation_result enum

Revision ID: add_inconclusive
Revises: 9f66600c3e18
Create Date: 2026-01-14
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'add_inconclusive'
down_revision = '9f66600c3e18'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'inconclusive' value to the evaluation_result enum
    op.execute("ALTER TYPE evaluation_result ADD VALUE IF NOT EXISTS 'inconclusive'")


def downgrade():
    # PostgreSQL doesn't support removing enum values easily
    # This would require recreating the type and all dependent columns
    pass
