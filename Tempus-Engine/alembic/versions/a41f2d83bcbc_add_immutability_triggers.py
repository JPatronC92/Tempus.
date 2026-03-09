"""add_immutability_triggers

Revision ID: a41f2d83bcbc
Revises: 530e942bffd9
Create Date: 2026-03-08 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a41f2d83bcbc'
down_revision: Union[str, None] = '530e942bffd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQL trigger to prevent any UPDATE or DELETE on decision_records
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_decision_alteration()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'DecisionRecords are cryptographically immutable by AI Governance rules. Updates and Deletes are strictly forbidden.';
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_prevent_decision_alteration
    BEFORE UPDATE OR DELETE ON decision_records
    FOR EACH ROW EXECUTE FUNCTION prevent_decision_alteration();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_decision_alteration ON decision_records;")
    op.execute("DROP FUNCTION IF EXISTS prevent_decision_alteration;")
