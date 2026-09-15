"""add todo and notification tables

Revision ID: 20260915_add_todo_and_notification
Revises: 20260522_add_clip_range
Create Date: 2026-09-15 17:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260915_add_todo_and_notification"
down_revision = "20260522_add_clip_range"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. 创建 todo 表
    if "todo" not in tables:
        op.create_table(
            "todo",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="待办ID"),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID"),
            sa.Column("title", sa.String(256), nullable=False, comment="待办标题"),
            sa.Column("description", sa.Text(), nullable=True, comment="待办详细描述"),
            sa.Column("priority", sa.String(16), nullable=False, server_default="medium", comment="优先级: low/medium/high"),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending", comment="状态: pending/completed"),
            sa.Column("due_time", sa.DateTime(), nullable=True, comment="截止到期时间"),
            sa.Column("remind_time", sa.DateTime(), nullable=True, comment="到期提醒时间"),
            sa.Column("is_reminded", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否已经触发提醒推送"),
            sa.Column("completed_at", sa.DateTime(), nullable=True, comment="完成时间"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        )
        op.create_index("ix_todo_user_id", "todo", ["user_id"])
        op.create_index("ix_todo_status", "todo", ["status"])
        op.create_index("ix_todo_remind_time", "todo", ["remind_time"])
        op.create_index("ix_todo_is_reminded", "todo", ["is_reminded"])

    # 2. 创建 notification 表
    if "notification" not in tables:
        op.create_table(
            "notification",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, comment="通知ID"),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, comment="接收用户ID"),
            sa.Column("title", sa.String(256), nullable=False, comment="通知标题"),
            sa.Column("content", sa.Text(), nullable=False, comment="通知内容"),
            sa.Column("type", sa.String(32), nullable=False, server_default="todo_reminder", comment="类型: todo_reminder/system"),
            sa.Column("related_id", sa.Integer(), nullable=True, comment="关联资源ID (如 todo_id)"),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否已读"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        )
        op.create_index("ix_notification_user_id", "notification", ["user_id"])
        op.create_index("ix_notification_is_read", "notification", ["is_read"])
        op.create_index("ix_notification_created_at", "notification", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "notification" in tables:
        op.drop_table("notification")

    if "todo" in tables:
        op.drop_table("todo")
