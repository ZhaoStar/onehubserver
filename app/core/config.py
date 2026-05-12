from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置，自动从 .env 文件读取"""

    # 应用
    APP_NAME: str = "OneHub"
    DEBUG: bool = True

    # 数据库 (MySQL)
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3307
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "onehub"
    DATABASE_URL: str = ""  # 自动拼接，也可手动指定

    # JWT
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # URL 编码密码，防止特殊字符（如 @ # % 等）破坏连接串
        encoded_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+aiomysql://{self.DB_USER}:{encoded_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
