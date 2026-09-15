from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.todo import (
    TodoCreate,
    TodoListOut,
    TodoPublic,
    TodoStatsSummary,
    TodoUpdate,
)
from app.services.todo import TodoService

router = APIRouter(prefix="/todos", tags=["待办事项管理"])


@router.post("", response_model=TodoPublic, status_code=status.HTTP_201_CREATED, summary="创建待办事项")
async def create_todo(
    db: DBSession,
    current_user: CurrentUser,
    todo_in: TodoCreate,
):
    """创建一条新的待办事项，支持设置优先级、截止时间与到期提醒时间"""
    return await TodoService.create(db, current_user.id, todo_in)


@router.get("", response_model=TodoListOut, summary="获取待办事项列表及统计")
async def list_todos(
    db: DBSession,
    current_user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status", description="状态过滤: pending/completed"),
    priority: str | None = Query(default=None, description="优先级过滤: low/medium/high"),
    search: str | None = Query(default=None, description="关键词模糊搜索"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    """获取当前登录用户的待办列表，并返回待办总体统计指标"""
    total, items = await TodoService.list_todos(
        db,
        current_user.id,
        status=status_filter,
        priority=priority,
        search=search,
        skip=skip,
        limit=limit,
    )
    stats = await TodoService.get_stats(db, current_user.id)
    return TodoListOut(
        total=total,
        items=[TodoPublic.model_validate(item) for item in items],
        stats=stats,
    )


@router.get("/stats", response_model=TodoStatsSummary, summary="获取待办统计汇总")
async def get_todo_stats(
    db: DBSession,
    current_user: CurrentUser,
):
    """获取待办总数、待完成数、已完成数、今日截止数、已超时数统计"""
    return await TodoService.get_stats(db, current_user.id)


@router.get("/{todo_id}", response_model=TodoPublic, summary="获取待办详情")
async def get_todo(
    db: DBSession,
    current_user: CurrentUser,
    todo_id: int,
):
    todo = await TodoService.get_by_id(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待办事项不存在")
    return todo


@router.put("/{todo_id}", response_model=TodoPublic, summary="更新待办事项")
async def update_todo(
    db: DBSession,
    current_user: CurrentUser,
    todo_id: int,
    todo_in: TodoUpdate,
):
    todo = await TodoService.get_by_id(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待办事项不存在")
    return await TodoService.update(db, todo, todo_in)


@router.patch("/{todo_id}/toggle", response_model=TodoPublic, summary="快速切换完成状态")
async def toggle_todo(
    db: DBSession,
    current_user: CurrentUser,
    todo_id: int,
):
    """在 pending（进行中）与 completed（已完成）之间快速切换"""
    todo = await TodoService.get_by_id(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待办事项不存在")
    return await TodoService.toggle_status(db, todo)


@router.delete("/completed/clear", summary="一键清空所有已完成待办")
async def clear_completed_todos(
    db: DBSession,
    current_user: CurrentUser,
):
    """一键删除当前登录用户所有已完成的待办事项"""
    count = await TodoService.clear_completed(db, current_user.id)
    return {"message": "已清空已完成待办", "count": count}


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除待办事项")
async def delete_todo(
    db: DBSession,
    current_user: CurrentUser,
    todo_id: int,
):
    todo = await TodoService.get_by_id(db, todo_id, current_user.id)
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="待办事项不存在")
    await TodoService.delete(db, todo)
