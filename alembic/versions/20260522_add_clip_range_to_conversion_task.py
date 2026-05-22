"""add clip range columns to conversion_task

Revision ID: 20260522_add_clip_range
Revises:
Create Date: 2026-05-22 13:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260522_add_clip_range"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("conversion_task")}

    if "clip_start_seconds" not in columns:
        op.add_column(
            "conversion_task",
            sa.Column("clip_start_seconds", sa.Float(), nullable=True, comment="截取开始时间(秒)"),
        )

    if "clip_end_seconds" not in columns:
        op.add_column(
            "conversion_task",
            sa.Column("clip_end_seconds", sa.Float(), nullable=True, comment="截取结束时间(秒)"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("conversion_task")}

    if "clip_end_seconds" in columns:
        op.drop_column("conversion_task", "clip_end_seconds")

    if "clip_start_seconds" in columns:
        op.drop_column("conversion_task", "clip_start_seconds")
