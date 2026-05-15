import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
from sqlalchemy import select, func

from app.api.deps import DBSession, CurrentUser
from app.models.conversion import ConversionTask
from app.schemas.conversion import (
    ConversionTaskOut,
    ConversionTaskListOut,
)
from app.services.conversion import (
    convert_video_to_mp3,
    ConversionError,
    create_conversion_task,
    _get_input_dir,
    _get_output_dir,
    get_duration,
)
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/convert", tags=["视频转MP3"])


# 允许的视频格式
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "flv", "wmv", "webm", "m4v", "3gp"}


def _get_ext(filename: str) -> str:
    """Get lowercase extension without dot, e.g. 'mp4'"""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _remove_file_if_exists(path: str | None) -> None:
    """尽力删除任务关联文件，不让文件系统异常影响接口主流程。"""
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


@router.post("/", response_model=ConversionTaskOut, status_code=status.HTTP_201_CREATED)
async def create_conversion(
    db: DBSession,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="视频文件"),
    bitrate: str = Form(default="192k", pattern=r"^\d+k$"),
    sample_rate: int = Form(default=44100, ge=8000, le=96000),
    channels: int = Form(default=2, ge=1, le=2),
):
    """上传视频，创建转换任务（后台异步转换）"""
    # 1. 格式校验
    ext = _get_ext(file.filename or "unknown")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的视频格式: .{ext}，支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # 2. 保存视频文件到磁盘
    input_dir = _get_input_dir()
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    input_path = os.path.join(str(input_dir), safe_name)

    file_size = 0
    chunk_size = 1024 * 1024  # 1MB
    max_bytes = settings.MAX_VIDEO_SIZE_MB * 1024 * 1024
    with open(input_path, "wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > max_bytes:
                # 超出上限，删除已保存的临时文件
                try:
                    os.remove(input_path)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"文件大小超过上限 {settings.MAX_VIDEO_SIZE_MB}MB",
                )
            f.write(chunk)

    # 3. 预生成输出路径
    output_dir = _get_output_dir()
    output_name = f"{uuid.uuid4().hex}.mp3"
    output_path = os.path.join(str(output_dir), output_name)

    # 4. 创建任务记录
    task = await create_conversion_task(
        db=db,
        user_id=current_user.id,
        filename=file.filename or "unknown",
        ext=ext,
        file_size=file_size,
        input_path=input_path,
        output_path=output_path,
        bitrate=bitrate,
        sample_rate=sample_rate,
        channels=channels,
    )
    task_id = task.id

    # 5. 提交数据库
    await db.commit()

    # 6. 添加后台任务
    background_tasks.add_task(_run_conversion, task_id, input_path, output_path, bitrate, sample_rate, channels)

    return task


async def _run_conversion(
    task_id: int,
    input_path: str,
    output_path: str,
    bitrate: str,
    sample_rate: int,
    channels: int,
):
    """后台转换任务——由 BackgroundTasks 调用"""
    from app.core.database import async_session_factory
    from sqlalchemy import select, update

    async with async_session_factory() as db:
        try:
            # 更新状态为 processing
            await db.execute(
                update(ConversionTask)
                .where(ConversionTask.id == task_id)
                .values(status="processing")
            )
            await db.commit()

            # 执行 FFmpeg 转换
            async for _ in convert_video_to_mp3(
                task_id, input_path, output_path, bitrate, sample_rate, channels
            ):
                pass  # 进度暂时不入库，后续可扩展 WebSocket

            # 获取时长和输出文件大小
            duration = get_duration(output_path)
            output_size = os.path.getsize(output_path)

            await db.execute(
                update(ConversionTask)
                .where(ConversionTask.id == task_id)
                .values(
                    status="completed",
                    duration=duration,
                    output_size=output_size,
                )
            )
            await db.commit()

            # 转换成功后不再保留源视频；删除失败不影响已完成任务。
            _remove_file_if_exists(input_path)

        except ConversionError as e:
            await db.execute(
                update(ConversionTask)
                .where(ConversionTask.id == task_id)
                .values(status="failed", error_message=str(e))
            )
            await db.commit()

        except Exception as e:
            await db.execute(
                update(ConversionTask)
                .where(ConversionTask.id == task_id)
                .values(status="failed", error_message=f"未知错误: {str(e)}")
            )
            await db.commit()


@router.get("/tasks", response_model=ConversionTaskListOut)
async def list_tasks(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 20,
):
    """我的转换任务列表"""
    total_q = select(func.count(ConversionTask.id)).where(
        ConversionTask.user_id == current_user.id
    )
    total = (await db.execute(total_q)).scalar() or 0

    stmt = (
        select(ConversionTask)
        .where(ConversionTask.user_id == current_user.id)
        .order_by(ConversionTask.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return ConversionTaskListOut(total=total, items=[ConversionTaskOut.model_validate(t) for t in items])


@router.delete("/tasks")
async def clear_tasks(
    db: DBSession,
    current_user: CurrentUser,
):
    """清空我的转换任务列表"""
    stmt = select(ConversionTask).where(ConversionTask.user_id == current_user.id)
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    file_paths = [
        path
        for task in tasks
        for path in (task.input_path, task.output_path)
        if path
    ]

    for task in tasks:
        await db.delete(task)
    await db.commit()

    for path in file_paths:
        _remove_file_if_exists(path)

    return {"deleted": len(tasks)}


@router.get("/tasks/{task_id}", response_model=ConversionTaskOut)
async def get_task(
    db: DBSession,
    current_user: CurrentUser,
    task_id: int,
):
    """查询单个任务详情"""
    stmt = select(ConversionTask).where(
        ConversionTask.id == task_id,
        ConversionTask.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    db: DBSession,
    current_user: CurrentUser,
    task_id: int,
):
    """删除我的转换任务（支持已完成和失败任务）"""
    stmt = select(ConversionTask).where(
        ConversionTask.id == task_id,
        ConversionTask.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status in {"pending", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"任务仍在处理中，当前状态: {task.status}",
        )

    input_path = task.input_path
    output_path = task.output_path
    await db.delete(task)
    await db.commit()

    _remove_file_if_exists(input_path)
    _remove_file_if_exists(output_path)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/download/{task_id}")
async def download_mp3(
    db: DBSession,
    current_user: CurrentUser,
    task_id: int,
):
    """下载转换完成的 MP3 文件"""
    stmt = select(ConversionTask).where(
        ConversionTask.id == task_id,
        ConversionTask.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务尚未完成，当前状态: {task.status}",
        )
    if task.output_path is None or not os.path.exists(task.output_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="输出文件不存在")

    # 下载文件名：原始文件名改扩展名为 .mp3
    original_name = task.original_filename.rsplit(".", 1)[0]
    download_name = f"{original_name}.mp3"

    return FileResponse(
        path=task.output_path,
        media_type="audio/mpeg",
        filename=download_name,
    )
