from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.notification import (
    NotificationListOut,
    NotificationPublic,
    UnreadCountOut,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["消息通知与提醒"])


@router.get("", response_model=NotificationListOut, summary="获取通知列表")
async def list_notifications(
    db: DBSession,
    current_user: CurrentUser,
    is_read: bool | None = Query(default=None, description="是否已读筛选"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """获取当前用户的消息通知列表"""
    total, unread_count, items = await NotificationService.list_notifications(
        db, current_user.id, is_read=is_read, skip=skip, limit=limit
    )
    return NotificationListOut(
        total=total,
        unread_count=unread_count,
        items=[NotificationPublic.model_validate(item) for item in items],
    )


@router.get("/unread-count", response_model=UnreadCountOut, summary="获取未读通知数")
async def get_unread_count(
    db: DBSession,
    current_user: CurrentUser,
):
    """获取当前用户的未读通知数量，供客户端铃铛/角标刷新"""
    count = await NotificationService.get_unread_count(db, current_user.id)
    return UnreadCountOut(unread_count=count)


@router.get("/poll-due", response_model=list[NotificationPublic], summary="轮询待办到期新提醒")
async def poll_due_reminders(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=50),
):
    """供移动端/Web端实时轮询最新触发的未读待办到期提醒"""
    items = await NotificationService.get_due_reminders(
        db, current_user.id, limit=limit
    )
    return [NotificationPublic.model_validate(item) for item in items]


@router.patch("/{notification_id}/read", status_code=status.HTTP_200_OK, summary="标记单条通知已读")
async def mark_notification_read(
    db: DBSession,
    current_user: CurrentUser,
    notification_id: int,
):
    success = await NotificationService.mark_as_read(
        db, notification_id, current_user.id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return {"message": "已标记为已读"}


@router.post("/read-all", status_code=status.HTTP_200_OK, summary="一键全部标记已读")
async def mark_all_notifications_read(
    db: DBSession,
    current_user: CurrentUser,
):
    updated = await NotificationService.mark_all_as_read(db, current_user.id)
    return {"message": "全部标记已读成功", "count": updated}
