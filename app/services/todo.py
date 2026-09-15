from datetime import datetime, time
from typing import Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoStatsSummary, TodoUpdate


class TodoService:
    @staticmethod
    async def create(db: AsyncSession, user_id: int, todo_in: TodoCreate) -> Todo:
        todo = Todo(
            user_id=user_id,
            title=todo_in.title,
            description=todo_in.description,
            priority=todo_in.priority,
            status="pending",
            due_time=todo_in.due_time,
            remind_time=todo_in.remind_time,
            is_reminded=False,
        )
        db.add(todo)
        await db.commit()
        await db.refresh(todo)
        return todo

    @staticmethod
    async def get_by_id(db: AsyncSession, todo_id: int, user_id: int) -> Todo | None:
        result = await db.execute(
            select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_todos(
        db: AsyncSession,
        user_id: int,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, Sequence[Todo]]:
        query = select(Todo).where(Todo.user_id == user_id)

        if status:
            query = query.where(Todo.status == status)
        if priority:
            query = query.where(Todo.priority == priority)
        if search:
            query = query.where(
                or_(
                    Todo.title.ilike(f"%{search}%"),
                    Todo.description.ilike(f"%{search}%"),
                )
            )

        # Count total matching records
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        # Order by: pending first, then remind_time / due_time asc (nulls last), then created_at desc
        query = (
            query.order_by(
                Todo.status.asc(),
                Todo.due_time.asc().nulls_last(),
                Todo.created_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        items = result.scalars().all()
        return total, items

    @staticmethod
    async def get_stats(db: AsyncSession, user_id: int) -> TodoStatsSummary:
        now = datetime.now()
        today_start = datetime.combine(now.date(), time.min)
        today_end = datetime.combine(now.date(), time.max)

        # 全量统计
        total_res = await db.execute(
            select(func.count(Todo.id)).where(Todo.user_id == user_id)
        )
        total = total_res.scalar() or 0

        pending_res = await db.execute(
            select(func.count(Todo.id)).where(
                Todo.user_id == user_id, Todo.status == "pending"
            )
        )
        pending_count = pending_res.scalar() or 0

        completed_count = total - pending_count

        # 今日截止（待完成且 due_time 在今天之间）
        due_today_res = await db.execute(
            select(func.count(Todo.id)).where(
                Todo.user_id == user_id,
                Todo.status == "pending",
                Todo.due_time >= today_start,
                Todo.due_time <= today_end,
            )
        )
        due_today_count = due_today_res.scalar() or 0

        # 已超时（待完成且 due_time < now）
        overdue_res = await db.execute(
            select(func.count(Todo.id)).where(
                Todo.user_id == user_id,
                Todo.status == "pending",
                Todo.due_time < now,
            )
        )
        overdue_count = overdue_res.scalar() or 0

        return TodoStatsSummary(
            total=total,
            pending_count=pending_count,
            completed_count=completed_count,
            due_today_count=due_today_count,
            overdue_count=overdue_count,
        )

    @staticmethod
    async def update(db: AsyncSession, todo: Todo, todo_in: TodoUpdate) -> Todo:
        update_data = todo_in.model_dump(exclude_unset=True)

        # 如果修改了提醒时间且提醒时间晚于当前时间，重置 is_reminded 状态
        if "remind_time" in update_data:
            new_remind = update_data["remind_time"]
            if new_remind and new_remind > datetime.now():
                todo.is_reminded = False

        if "status" in update_data:
            if update_data["status"] == "completed" and todo.status != "completed":
                todo.completed_at = datetime.now()
            elif update_data["status"] == "pending":
                todo.completed_at = None

        for field, value in update_data.items():
            setattr(todo, field, value)

        await db.commit()
        await db.refresh(todo)
        return todo

    @staticmethod
    async def toggle_status(db: AsyncSession, todo: Todo) -> Todo:
        if todo.status == "completed":
            todo.status = "pending"
            todo.completed_at = None
        else:
            todo.status = "completed"
            todo.completed_at = datetime.now()

        await db.commit()
        await db.refresh(todo)
        return todo

    @staticmethod
    async def delete(db: AsyncSession, todo: Todo) -> None:
        await db.delete(todo)
        await db.commit()

    @staticmethod
    async def clear_completed(db: AsyncSession, user_id: int) -> int:
        from sqlalchemy import delete as sql_delete
        result = await db.execute(
            sql_delete(Todo).where(Todo.user_id == user_id, Todo.status == "completed")
        )
        await db.commit()
        return result.rowcount

