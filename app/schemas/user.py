from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- 请求 ----------

class UserRegister(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=64, examples=["zhangsan"])
    email: EmailStr = Field(..., examples=["zhangsan@example.com"])
    password: str = Field(..., min_length=6, max_length=128, examples=["abc123"])
    nickname: str | None = None


class UserLogin(BaseModel):
    """登录请求"""
    username: str = Field(..., examples=["zhangsan"])
    password: str = Field(..., examples=["abc123"])
    captcha_key: str = Field(..., description="验证码 key，从 /auth/captcha 获取")
    captcha_code: str = Field(..., description="验证码内容")


class CaptchaOut(BaseModel):
    """验证码响应（key 放在 header 中，这里仅作说明）"""
    pass


class UserCreate(BaseModel):
    """管理员创建用户请求"""
    username: str = Field(..., min_length=3, max_length=64, examples=["zhangsan"])
    email: EmailStr = Field(..., examples=["zhangsan@example.com"])
    password: str = Field(..., min_length=6, max_length=128, examples=["abc123"])
    nickname: str | None = Field(default=None, max_length=64)
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    """管理员更新用户请求"""
    username: str | None = Field(default=None, min_length=3, max_length=64)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None
    is_superuser: bool | None = None


# ---------- 响应 ----------

class UserPublic(BaseModel):
    """公开的用户信息（不含密码）"""
    id: int
    username: str
    email: str
    nickname: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT 令牌响应"""
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """登录成功响应"""
    token: Token
    user: UserPublic


class UserListOut(BaseModel):
    """用户列表响应"""
    total: int
    items: list[UserPublic]
