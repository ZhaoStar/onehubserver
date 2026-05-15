import os

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentSuperUser, DBSession
from app.models.conversion import ConversionTask
from app.models.user import User
from app.schemas.user import UserCreate, UserListOut, UserPublic, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])


def _remove_file_if_exists(path: str | None) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


async def _ensure_unique_user_fields(
    db: DBSession,
    username: str | None = None,
    email: str | None = None,
    exclude_user_id: int | None = None,
) -> None:
    if username is not None:
        user = await UserService.get_by_username(db, username)
        if user is not None and user.id != exclude_user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已被注册")

    if email is not None:
        user = await UserService.get_by_email(db, email)
        if user is not None and user.id != exclude_user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")


@router.get("", response_model=UserListOut)
async def list_users(
    db: DBSession,
    current_user: CurrentSuperUser,
    skip: int = 0,
    limit: int = 20,
):
    """用户列表"""
    total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    return UserListOut(total=total, items=[UserPublic.model_validate(user) for user in users])


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    db: DBSession,
    current_user: CurrentSuperUser,
    data: UserCreate,
):
    """创建用户"""
    await _ensure_unique_user_fields(db, username=data.username, email=data.email)
    user = await UserService.create_user(
        db=db,
        username=data.username,
        email=str(data.email),
        password=data.password,
        nickname=data.nickname,
        is_active=data.is_active,
        is_superuser=data.is_superuser,
    )
    await db.commit()
    return user


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    db: DBSession,
    current_user: CurrentSuperUser,
    user_id: int,
):
    """查询用户详情"""
    user = await UserService.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    db: DBSession,
    current_user: CurrentSuperUser,
    user_id: int,
    data: UserUpdate,
):
    """更新用户信息、激活状态和超级管理员状态"""
    user = await UserService.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    values = data.model_dump(exclude_unset=True)
    for required_field in ("username", "email", "password", "is_active", "is_superuser"):
        if required_field in values and values[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{required_field} 不能为 null",
            )

    await _ensure_unique_user_fields(
        db,
        username=values.get("username"),
        email=str(values["email"]) if values.get("email") is not None else None,
        exclude_user_id=user.id,
    )

    if user.id == current_user.id:
        if values.get("is_active") is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能停用当前登录用户")
        if values.get("is_superuser") is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能取消当前登录用户的超级管理员权限")

    if "email" in values and values["email"] is not None:
        values["email"] = str(values["email"])

    user = await UserService.update_user(db, user, **values)
    await db.commit()
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    db: DBSession,
    current_user: CurrentSuperUser,
    user_id: int,
):
    """删除用户，并清理该用户的转换文件"""
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录用户")

    user = await UserService.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    result = await db.execute(select(ConversionTask).where(ConversionTask.user_id == user.id))
    tasks = result.scalars().all()
    file_paths = [
        path
        for task in tasks
        for path in (task.input_path, task.output_path)
        if path
    ]

    await db.delete(user)
    await db.commit()

    for path in file_paths:
        _remove_file_if_exists(path)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
