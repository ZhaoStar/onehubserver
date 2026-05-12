from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """用户表"""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, comment="8位随机唯一ID")
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="用户名")
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False, comment="邮箱")
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False, comment="密码哈希")
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="昵称")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否激活")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否超级管理员")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
