from datetime import datetime
from pydantic import BaseModel


class NotificationPublic(BaseModel):
    """通知详情响应"""
    id: int
    user_id: int
    title: str
    content: str
    type: str
    related_id: int | None = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListOut(BaseModel):
    """通知列表响应"""
    total: int
    unread_count: int
    items: list[NotificationPublic]


class UnreadCountOut(BaseModel):
    """未读数统计响应"""
    unread_count: int
