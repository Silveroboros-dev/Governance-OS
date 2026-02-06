"""Add narrative_memo to evidence_packs

Revision ID: add_narrative_memo
Revises: 157371e0464b
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_narrative_memo'
down_revision: Union[str, Sequence[str], None] = '157371e0464b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add narrative_memo column to evidence_packs table."""
    op.add_column(
        'evidence_packs',
        sa.Column('narrative_memo', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    """Remove narrative_memo column from evidence_packs table."""
    op.drop_column('evidence_packs', 'narrative_memo')
