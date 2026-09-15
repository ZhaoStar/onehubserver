import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.notification import Notification
from app.models.todo import Todo

logger = logging.getLogger("onehub.reminder")


async def check_and_push_todo_reminders() -> int:
    """
    扫描当前到达提醒时间且尚未推送提醒的待办事项，
    自动生成消息通知并标记待办为已提醒。
    """
    now = datetime.now()
    count = 0

    async with async_session_factory() as session:
        try:
            # 查找已到提醒时间、待办仍为进行中、且未推送过的记录
            stmt = (
                select(Todo)
                .where(
                    Todo.status == "pending",
                    Todo.is_reminded == False,
                    Todo.remind_time.is_not(None),
                    Todo.remind_time <= now,
                )
                .limit(100)
            )
            result = await session.execute(stmt)
            due_todos = result.scalars().all()

            if not due_todos:
                return 0

            for todo in due_todos:
                # 生成提醒通知
                notification = Notification(
                    user_id=todo.user_id,
                    title="待办到期提醒",
                    content=f"您的待办【{todo.title}】已到设定提醒时间，请及时处理！",
                    type="todo_reminder",
                    related_id=todo.id,
                    is_read=False,
                )
                session.add(notification)
                todo.is_reminded = True
                count += 1

                logger.info(
                    "触发待办到期提醒: todo_id=%s, user_id=%s, title=%s",
                    todo.id,
                    todo.user_id,
                    todo.title,
                )

            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("待办到期提醒巡检执行异常")
            return 0

    return count


async def run_todo_reminder_loop(interval_sec: int = 20) -> None:
    """
    后台常驻异步轮询任务：每隔 interval_sec 秒扫描一次待办到期提醒
    """
    logger.info("待办后台到期提醒轮询服务已启动 (巡检间隔: %ds)", interval_sec)
    while True:
        try:
            await asyncio.sleep(interval_sec)
            pushed_count = await check_and_push_todo_reminders()
            if pushed_count > 0:
                logger.info("本轮成功推送 %d 条待办到期提醒", pushed_count)
        except asyncio.CancelledError:
            logger.info("待办后台到期提醒轮询服务已停止")
            break
        except Exception:
            logger.exception("待办后台轮询主循环异常")
            await asyncio.sleep(interval_sec)
