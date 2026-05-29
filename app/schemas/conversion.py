from datetime import datetime

from pydantic import BaseModel, Field


# ---------- 请求 ----------

class ConvertRequest(BaseModel):
    """转换请求（参数通过表单字段传递）"""
    bitrate: str = Field(default="192k", pattern=r"^\d+k$", description="比特率 128k/192k/320k")
    sample_rate: int = Field(default=44100, ge=8000, le=96000, description="采样率（Hz）")
    channels: int = Field(default=2, ge=1, le=2, description="声道数 1=单声道 2=立体声")
    start_time: str | None = Field(default=None, description="截取开始时间，支持 SS / MM:SS / HH:MM:SS(.ms)")
    end_time: str | None = Field(default=None, description="截取结束时间，支持 SS / MM:SS / HH:MM:SS(.ms)")


class RemoteConvertRequest(BaseModel):
    """远程 URL 直转 MP3 请求"""
    url: str = Field(..., description="远程视频URL，支持 HTTP/HTTPS")
    bitrate: str = Field(default="192k", pattern=r"^\d+k$", description="比特率 128k/192k/320k")
    sample_rate: int = Field(default=44100, ge=8000, le=96000, description="采样率（Hz）")
    channels: int = Field(default=2, ge=1, le=2, description="声道数 1=单声道 2=立体声")
    start_time: str | None = Field(default=None, description="截取开始时间，支持 SS / MM:SS / HH:MM:SS(.ms)")
    end_time: str | None = Field(default=None, description="截取结束时间，支持 SS / MM:SS / HH:MM:SS(.ms)")


# ---------- 响应 ----------

class ConversionTaskOut(BaseModel):
    """转换任务响应"""
    id: int
    user_id: int
    original_filename: str
    original_format: str
    file_size: int
    status: str
    bitrate: str
    sample_rate: int
    channels: int
    clip_start_seconds: float | None
    clip_end_seconds: float | None
    duration: float | None
    output_size: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversionTaskListOut(BaseModel):
    """转换任务列表"""
    total: int
    items: list[ConversionTaskOut]
