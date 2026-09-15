from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


class NotificationService:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        title: str,
        content: str,
        type: str = "todo_reminder",
        related_id: int | None = None,
    ) -> Notification:
        item = Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=type,
            related_id=related_id,
            is_read=False,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def list_notifications(
        db: AsyncSession,
        user_id: int,
        is_read: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, int, Sequence[Notification]]:
        query = select(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)

        total_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_query)).scalar() or 0

        unread_count_query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read == False
        )
        unread_count = (await db.execute(unread_count_query)).scalar() or 0

        query = (
            query.order_by(Notification.is_read.asc(), Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        items = result.scalars().all()
        return total, unread_count, items

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: int) -> int:
        query = select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.is_read == False
        )
        return (await db.execute(query)).scalar() or 0

    @staticmethod
    async def get_due_reminders(
        db: AsyncSession, user_id: int, limit: int = 10
    ) -> Sequence[Notification]:
        """获取最近未读的到期提醒，供客户端轮询"""
        query = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.type == "todo_reminder",
                Notification.is_read == False,
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def mark_as_read(
        db: AsyncSession, notification_id: int, user_id: int
    ) -> bool:
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        notification.is_read = True
        await db.commit()
        return True

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await db.commit()
        return result.rowcount
