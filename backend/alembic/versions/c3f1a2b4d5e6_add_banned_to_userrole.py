"""add_banned_to_userrole

Revision ID: c3f1a2b4d5e6
Revises: 0cb91d6a393e
Create Date: 2026-05-31 00:00:00.000000

Adds the 'banned' value to the userrole PostgreSQL enum type so that admins
can ban user accounts via POST /api/admin/users/{id}/ban.

PostgreSQL 12+ allows ALTER TYPE ... ADD VALUE inside a transaction block,
which is what Alembic uses by default. Since the project targets PostgreSQL 16
this migration is safe to run as-is.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3f1a2b4d5e6'
down_revision: Union[str, Sequence[str], None] = '0cb91d6a393e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'banned'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # A safe downgrade would require: create new enum, alter column, drop old enum.
    # For now this is intentionally left as a no-op; the extra value is harmless.
    pass
