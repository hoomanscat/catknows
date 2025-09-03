"""add skool_tag to members

Revision ID: 20250903_add_skool_tag
Revises: 91a47e89b116_fix_memberdailysnapshot_autoincrement_id
Create Date: 2025-09-03 00:00:00.000000
"""
from alembic import op  # type: ignore
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250903_add_skool_tag'
down_revision = '91a47e89b116'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # SQLite: add column if not exists
    try:
        op.add_column('members', sa.Column('skool_tag', sa.String(), nullable=True))
    except Exception:
        # best-effort for older sqlite without ALTER support
        pass


def downgrade() -> None:
    try:
        op.drop_column('members', 'skool_tag')
    except Exception:
        pass
