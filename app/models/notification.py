from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notification(Base):
    """消息通知/推送提醒表"""
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="通知ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="接收用户ID",
    )

    title: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="通知标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="通知内容"
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="todo_reminder",
        comment="类型: todo_reminder/system",
    )
    related_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="关联资源ID (如 todo_id)"
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True, comment="是否已读"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, title={self.title}, is_read={self.is_read})>"
