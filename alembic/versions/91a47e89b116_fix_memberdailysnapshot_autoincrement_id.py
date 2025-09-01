"""fix: MemberDailySnapshot autoincrement id (sqlite safe no-op)

Revision ID: 91a47e89b116
Revises: <DEINE_PREV_REV_ID_HIER_EINTRAGEN>
Create Date: 2025-09-01 11:07:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "91a47e89b116"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # SQLite kann kein ALTER COLUMN ... SET DEFAULT usw.
    # Unser Model ist bereits korrekt (id = Integer PK autoincrement).
    # Daher keine DB-Änderung erforderlich.
    pass


def downgrade():
    # No-op downgrade
    pass
