"""add joined_at_utc to members

Revision ID: 20250904_add_joined_at_utc
Revises: 20250903_add_skool_tag
Create Date: 2025-09-04 00:00:00.000000
"""
from alembic import op  # type: ignore
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250904_add_joined_at_utc'
down_revision = '20250903_add_skool_tag'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Best-effort: add nullable text column for joined_at_utc
    try:
        op.add_column('members', sa.Column('joined_at_utc', sa.String(), nullable=True))
    except Exception:
        # SQLite may not support ALTER in some environments — this is best-effort
        pass


def downgrade() -> None:
    try:
        op.drop_column('members', 'joined_at_utc')
    except Exception:
        pass
