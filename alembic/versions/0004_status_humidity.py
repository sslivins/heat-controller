"""status humidity

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24 11:20:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('device_status_cache', sa.Column('humidity', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Downgrades are intentionally unsupported in this project.  If you need
    # to revert a schema change, write a new forward migration that undoes it.
    raise NotImplementedError("downgrade not supported")
