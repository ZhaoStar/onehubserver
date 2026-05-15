from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from app.models.user import User
from app.core.security import hash_password, verify_password


class UserService:
    """用户相关业务逻辑"""

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> User | None:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def _generate_unique_id(db: AsyncSession) -> int:
        """生成8位不重复随机ID，最多重试5次"""
        for _ in range(5):
            uid = 10000000 + secrets.randbelow(90000000)
            result = await db.execute(select(User.id).where(User.id == uid))
            if result.scalar_one_or_none() is None:
                return uid
        raise RuntimeError("无法生成唯一ID，请稍后重试")

    @staticmethod
    async def create_user(
        db: AsyncSession,
        username: str,
        email: str,
        password: str,
        nickname: str | None = None,
        is_active: bool = False,
        is_superuser: bool = False,
    ) -> User:
        user = User(
            id=await UserService._generate_unique_id(db),
            username=username,
            email=email,
            hashed_password=hash_password(password),
            nickname=nickname,
            is_active=is_active,
            is_superuser=is_superuser,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_user(db: AsyncSession, user: User, **values) -> User:
        """更新用户字段；password 会转换为 hashed_password。"""
        password = values.pop("password", None)
        for field, value in values.items():
            setattr(user, field, value)
        if password is not None:
            user.hashed_password = hash_password(password)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
        """验证用户名和密码，成功返回 User，失败返回 None"""
        user = await UserService.get_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
