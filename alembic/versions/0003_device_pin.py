"""device pin

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24 17:55:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('pin', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Downgrades are intentionally unsupported in this project.  If you need
    # to revert a schema change, write a new forward migration that undoes it.
    raise NotImplementedError("downgrade not supported")
