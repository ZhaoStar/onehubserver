import os
import shutil
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings
from functools import lru_cache


# 项目根目录（app/ 的上级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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

    # —————— 视频转 MP3 配置 ——————
    # FFmpeg 可执行文件路径（留空则自动探测）
    FFMPEG_PATH: str = ""
    # 上传文件存放根目录
    UPLOAD_DIR: str = str(PROJECT_ROOT / "uploads")
    # 单次上传视频大小上限（MB）
    MAX_VIDEO_SIZE_MB: int = 500
    # 默认音频比特率（如 128k / 192k / 320k）
    DEFAULT_AUDIO_BITRATE: str = "192k"
    # 默认采样率
    DEFAULT_SAMPLE_RATE: int = 44100
    # 默认声道数（1=单声道, 2=立体声）
    DEFAULT_AUDIO_CHANNELS: int = 2

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

    def get_ffmpeg_path(self) -> str:
        """跨平台获取 FFmpeg 路径"""
        if self.FFMPEG_PATH:
            return self.FFMPEG_PATH
        # Windows 上 shutil.which 会自动补 .exe；Linux 上找 ffmpeg
        found = shutil.which("ffmpeg")
        if found:
            return found
        # 兜底：直接用 "ffmpeg"，依赖 PATH 环境变量
        return "ffmpeg"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
