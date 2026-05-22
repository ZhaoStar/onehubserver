from sqlalchemy import BigInteger, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ConversionTask(Base, TimestampMixin):
    """视频转 MP3 任务表"""
    __tablename__ = "conversion_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="任务ID")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True, comment="上传用户ID"
    )

    # 上传信息
    original_filename: Mapped[str] = mapped_column(String(256), nullable=False, comment="原始文件名")
    original_format: Mapped[str] = mapped_column(String(16), nullable=False, comment="原始格式，如 mp4/mov/avi")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="文件大小(字节)")

    # 状态
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending",
        comment="pending/processing/completed/failed"
    )

    # 文件路径
    input_path: Mapped[str] = mapped_column(String(512), nullable=False, comment="视频存放路径")
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="MP3输出路径")

    # 音频参数
    bitrate: Mapped[str] = mapped_column(String(16), nullable=False, default="192k", comment="音频比特率")
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=44100, comment="采样率")
    channels: Mapped[int] = mapped_column(Integer, nullable=False, default=2, comment="声道数")
    clip_start_seconds: Mapped[float | None] = mapped_column(Float, nullable=True, comment="截取开始时间(秒)")
    clip_end_seconds: Mapped[float | None] = mapped_column(Float, nullable=True, comment="截取结束时间(秒)")

    # 结果信息
    duration: Mapped[float | None] = mapped_column(Float, nullable=True, comment="音频时长(秒)")
    output_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="输出文件大小(字节)")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")

    def __repr__(self) -> str:
        return f"<ConversionTask(id={self.id}, status={self.status})>"
