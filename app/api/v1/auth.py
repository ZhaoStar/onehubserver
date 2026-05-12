from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import DBSession, CurrentUser
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserPublic,
    Token,
    LoginResponse,
)
from app.services.user import UserService
from app.core.security import create_access_token
from app.core.captcha import generate_code, generate_captcha_image, store_code, verify_code

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/captcha")
async def get_captcha():
    """获取图片验证码，返回 PNG 图片 + X-Captcha-Key 响应头"""
    code = generate_code()
    key = store_code(code)
    image_buf = generate_captcha_image(code)
    return StreamingResponse(
        image_buf,
        media_type="image/png",
        headers={"X-Captcha-Key": key, "Cache-Control": "no-cache, no-store"},
    )


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(db: DBSession, data: UserRegister):
    """用户注册"""
    # 检查用户名是否已存在
    if await UserService.get_by_username(db, data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被注册")
    # 检查邮箱是否已存在
    if await UserService.get_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")
    # 创建用户
    user = await UserService.create_user(
        db, data.username, data.email, data.password, data.nickname
    )
    return user


@router.post("/login", response_model=LoginResponse)
async def login(db: DBSession, data: UserLogin):
    """用户登录（需先调用 GET /auth/captcha 获取验证码）"""
    # 验证验证码
    if not verify_code(data.captcha_key, data.captcha_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期，请刷新重试",
        )
    user = await UserService.authenticate(db, data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(data={"sub": str(user.id)})
    return LoginResponse(
        token=Token(access_token=token),
        user=user,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: CurrentUser):
    """获取当前登录用户信息（需要 token）"""
    return current_user
