from datetime import datetime
from pydantic import BaseModel, Field


# ---------- 请求模型 ----------

class TodoCreate(BaseModel):
    """创建待办请求"""
    title: str = Field(..., min_length=1, max_length=256, description="待办标题")
    description: str | None = Field(default=None, description="详细描述")
    priority: str = Field(default="medium", description="优先级: low/medium/high")
    due_time: datetime | None = Field(default=None, description="截止到期时间")
    remind_time: datetime | None = Field(default=None, description="到期提醒时间")


class TodoUpdate(BaseModel):
    """更新待办请求"""
    title: str | None = Field(default=None, min_length=1, max_length=256, description="待办标题")
    description: str | None = Field(default=None, description="详细描述")
    priority: str | None = Field(default=None, description="优先级: low/medium/high")
    status: str | None = Field(default=None, description="状态: pending/completed")
    due_time: datetime | None = Field(default=None, description="截止到期时间")
    remind_time: datetime | None = Field(default=None, description="到期提醒时间")
    is_reminded: bool | None = Field(default=None, description="是否已提醒")


# ---------- 响应模型 ----------

class TodoPublic(BaseModel):
    """待办详情响应"""
    id: int
    user_id: int
    title: str
    description: str | None = None
    priority: str
    status: str
    due_time: datetime | None = None
    remind_time: datetime | None = None
    is_reminded: bool
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TodoStatsSummary(BaseModel):
    """待办统计信息"""
    total: int = 0
    pending_count: int = 0
    completed_count: int = 0
    due_today_count: int = 0
    overdue_count: int = 0


class TodoListOut(BaseModel):
    """待办列表分页响应"""
    total: int
    items: list[TodoPublic]
    stats: TodoStatsSummary
