from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()


class UploadInitRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=256)
    file_size: int = Field(..., gt=0)
    total_chunks: int = Field(..., ge=1, le=settings.MAX_CHUNK_COUNT)
    chunk_size: int = Field(..., gt=0, le=settings.MAX_CHUNK_SIZE_MB * 1024 * 1024)


class UploadInitResponse(BaseModel):
    upload_id: str
    chunks_received: list[int]
    total_chunks: int
    chunk_size: int


class ChunkUploadResponse(BaseModel):
    upload_id: str
    chunk_index: int
    received: bool
    chunks_received: list[int]
    received_count: int
    total_chunks: int
    all_received: bool


class UploadCompleteRequest(BaseModel):
    bitrate: str = Field(default="192k", pattern=r"^\d+k$")
    sample_rate: int = Field(default=44100, ge=8000, le=96000)
    channels: int = Field(default=2, ge=1, le=2)


class UploadStatusResponse(BaseModel):
    upload_id: str
    filename: str
    total_chunks: int
    chunks_received: list[int]
    received_count: int
    all_received: bool
    created_at: str
