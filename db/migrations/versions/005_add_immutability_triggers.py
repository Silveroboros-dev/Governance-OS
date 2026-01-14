"""Add immutability triggers for decisions, evidence_packs, and audit_events.

These triggers enforce database-level immutability, preventing UPDATE or DELETE
operations even with direct database access. This is critical for audit-grade
evidence integrity.

Revision ID: 005_add_immutability_triggers
Revises: 004_add_approval_rules
Create Date: 2026-01-14
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '005_add_immutability_triggers'
down_revision = '004_add_approval_rules'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the function that prevents modifications
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Table % is immutable. UPDATE and DELETE operations are not allowed.',
                TG_TABLE_NAME
                USING HINT = 'This table is part of the audit trail and cannot be modified.';
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Add trigger to decisions table
    op.execute("""
        CREATE TRIGGER decisions_immutable
            BEFORE UPDATE OR DELETE ON decisions
            FOR EACH ROW
            EXECUTE FUNCTION prevent_modification();
    """)

    # Add trigger to evidence_packs table
    op.execute("""
        CREATE TRIGGER evidence_packs_immutable
            BEFORE UPDATE OR DELETE ON evidence_packs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_modification();
    """)

    # Add trigger to audit_events table
    op.execute("""
        CREATE TRIGGER audit_events_immutable
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW
            EXECUTE FUNCTION prevent_modification();
    """)

    # Add comment explaining the immutability
    op.execute("""
        COMMENT ON TABLE decisions IS
        'Immutable record of decisions. UPDATE/DELETE blocked by trigger.';
    """)
    op.execute("""
        COMMENT ON TABLE evidence_packs IS
        'Immutable evidence bundles. UPDATE/DELETE blocked by trigger.';
    """)
    op.execute("""
        COMMENT ON TABLE audit_events IS
        'Append-only audit trail. UPDATE/DELETE blocked by trigger.';
    """)


def downgrade() -> None:
    # Remove triggers
    op.execute("DROP TRIGGER IF EXISTS decisions_immutable ON decisions;")
    op.execute("DROP TRIGGER IF EXISTS evidence_packs_immutable ON evidence_packs;")
    op.execute("DROP TRIGGER IF EXISTS audit_events_immutable ON audit_events;")

    # Remove the function
    op.execute("DROP FUNCTION IF EXISTS prevent_modification();")

    # Remove comments
    op.execute("COMMENT ON TABLE decisions IS NULL;")
    op.execute("COMMENT ON TABLE evidence_packs IS NULL;")
    op.execute("COMMENT ON TABLE audit_events IS NULL;")
