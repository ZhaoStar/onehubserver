from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Todo(Base, TimestampMixin):
    """待办事项表"""
    __tablename__ = "todo"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="待办ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户ID",
    )

    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="待办标题"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="待办详细描述"
    )

    # 优先级: low, medium, high
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium", comment="优先级: low/medium/high"
    )

    # 状态: pending, completed
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
        comment="状态: pending/completed",
    )

    # 时间相关
    due_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="截止到期时间"
    )
    remind_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="到期提醒时间"
    )
    is_reminded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="是否已经触发提醒推送",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )

    def __repr__(self) -> str:
        return f"<Todo(id={self.id}, user_id={self.user_id}, title={self.title}, status={self.status})>"
