import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.background import BackgroundTasks
from sqlalchemy import select

from app.api.deps import DBSession, CurrentUser
from app.schemas.conversion import ConversionTaskOut
from app.schemas.upload import (
    UploadInitRequest,
    UploadInitResponse,
    ChunkUploadResponse,
    UploadCompleteRequest,
    UploadStatusResponse,
)
from app.services.chunk_upload import get_chunk_manager
from app.services.conversion import (
    create_conversion_task,
    _get_output_dir,
    get_duration,
    remove_file_if_exists,
    validate_clip_range,
)
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/upload", tags=["分块上传"])

# 与 convert.py 保持一致
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "flv", "wmv", "webm", "m4v", "3gp"}


def _get_ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


@router.post("/init", response_model=UploadInitResponse, status_code=status.HTTP_201_CREATED)
async def init_upload(
    current_user: CurrentUser,
    body: UploadInitRequest,
):
    """初始化分块上传会话"""
    ext = _get_ext(body.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的视频格式: .{ext}，支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    max_bytes = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
    if body.file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过上限 {settings.MAX_VIDEO_SIZE_MB}MB",
        )

    manager = get_chunk_manager()
    session = await manager.create_session(
        user_id=current_user.id,
        filename=body.filename,
        file_size=body.file_size,
        total_chunks=body.total_chunks,
        chunk_size=body.chunk_size,
    )

    return UploadInitResponse(
        upload_id=session.upload_id,
        chunks_received=[],
        total_chunks=session.total_chunks,
        chunk_size=session.chunk_size,
    )


@router.post("/{upload_id}/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    current_user: CurrentUser,
    upload_id: str,
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
):
    """上传一个分块"""
    manager = get_chunk_manager()
    session = await manager.get_session(upload_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="上传会话不存在或已过期")

    if chunk_index < 0 or chunk_index >= session.total_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"chunk_index 必须在 0 到 {session.total_chunks - 1} 之间",
        )

    chunk_data = await file.read()
    session = await manager.add_chunk(upload_id, current_user.id, chunk_index, chunk_data)

    received = sorted(session.chunks_received)
    return ChunkUploadResponse(
        upload_id=upload_id,
        chunk_index=chunk_index,
        received=True,
        chunks_received=received,
        received_count=len(received),
        total_chunks=session.total_chunks,
        all_received=session.all_received(),
    )


@router.post("/{upload_id}/complete", response_model=ConversionTaskOut, status_code=status.HTTP_201_CREATED)
async def complete_upload(
    db: DBSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    upload_id: str,
    body: UploadCompleteRequest,
):
    """合并分块并创建转换任务"""
    from app.api.v1.convert import _run_conversion

    manager = get_chunk_manager()
    session = await manager.get_session(upload_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="上传会话不存在或已过期")

    if not session.all_received():
        missing = session.missing_chunks()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"仍有 {len(missing)} 个分块未上传，缺失索引: {missing}",
        )

    result = await manager.complete_upload(upload_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="合并分块失败")

    input_path, file_size, filename = result
    ext = session.ext
    source_duration = get_duration(input_path)
    try:
        clip_start_seconds, clip_end_seconds = validate_clip_range(
            body.start_time,
            body.end_time,
            source_duration=source_duration,
        )
    except ValueError as exc:
        remove_file_if_exists(input_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    output_dir = _get_output_dir()
    output_name = f"{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(str(output_dir), output_name)

    task = await create_conversion_task(
        db=db,
        user_id=current_user.id,
        filename=filename,
        ext=ext,
        file_size=file_size,
        input_path=input_path,
        output_path=output_path,
        bitrate=body.bitrate,
        sample_rate=body.sample_rate,
        channels=body.channels,
        clip_start_seconds=clip_start_seconds,
        clip_end_seconds=clip_end_seconds,
    )
    task_id = task.id
    await db.commit()

    background_tasks.add_task(
        _run_conversion, task_id, input_path, output_path,
        body.bitrate, body.sample_rate, body.channels,
        clip_start_seconds, clip_end_seconds,
    )

    return task


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def upload_status(
    current_user: CurrentUser,
    upload_id: str,
):
    """查询上传会话状态（用于断点续传）"""
    from datetime import datetime, timezone

    manager = get_chunk_manager()
    session = await manager.get_session(upload_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="上传会话不存在或已过期")

    received = sorted(session.chunks_received)
    created_str = datetime.fromtimestamp(session.created_at, tz=timezone.utc).isoformat()

    return UploadStatusResponse(
        upload_id=session.upload_id,
        filename=session.filename,
        total_chunks=session.total_chunks,
        chunks_received=received,
        received_count=len(received),
        all_received=session.all_received(),
        created_at=created_str,
    )
