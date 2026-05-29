import asyncio
import os
import re
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import urlparse

import aiofiles
import httpx

from app.core.config import get_settings
from app.models.conversion import ConversionTask

settings = get_settings()


class ConversionError(Exception):
    """FFmpeg 转换异常"""
    pass


class DownloadError(Exception):
    """远程视频下载异常"""
    pass


CONTENT_TYPE_TO_EXT = {
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/x-msvideo": "avi",
    "video/x-matroska": "mkv",
    "video/x-flv": "flv",
    "video/x-ms-wmv": "wmv",
    "video/webm": "webm",
    "video/x-m4v": "m4v",
    "video/3gpp": "3gp",
}


async def download_remote_video(
    url: str,
    dest_path: str,
    max_size_bytes: int,
    timeout: int = 600,
) -> tuple[str, str, int]:
    """
    从远程 URL 流式下载视频文件。

    Returns:
        (original_filename, extension, file_size)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        ),
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()

            # 从 Content-Type 检测扩展名
            content_type = response.headers.get("content-type", "")
            content_type = content_type.split(";")[0].strip().lower()
            ext = CONTENT_TYPE_TO_EXT.get(content_type)

            # 备选：从 URL 路径提取扩展名
            if ext is None:
                url_path = urlparse(url).path
                if "." in url_path:
                    url_ext = url_path.rsplit(".", 1)[-1].lower()
                    if url_ext and len(url_ext) <= 6:
                        ext = url_ext

            if not ext:
                raise DownloadError(
                    "无法识别视频格式，请确认 URL 指向有效的视频文件"
                )

            # 从 URL 提取原始文件名
            url_path = urlparse(url).path
            raw_name = url_path.rsplit("/", 1)[-1] if "/" in url_path else url_path
            if not raw_name or "." not in raw_name:
                raw_name = f"video.{ext}"

            # 流式写入磁盘
            file_size = 0
            chunk_size = 1024 * 1024  # 1MB
            async with aiofiles.open(dest_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size):
                    file_size += len(chunk)
                    if file_size > max_size_bytes:
                        raise DownloadError(
                            f"文件大小超过上限 {max_size_bytes // (1024 * 1024)}MB"
                        )
                    await f.write(chunk)

            if file_size == 0:
                raise DownloadError("下载的文件为空")

            return raw_name, ext, file_size


TIME_PART_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")


def _ensure_dir(path: str) -> Path:
    """确保目录存在（跨平台）"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_input_dir() -> Path:
    return _ensure_dir(os.path.join(settings.UPLOAD_DIR, "videos"))


def _get_output_dir() -> Path:
    return _ensure_dir(os.path.join(settings.UPLOAD_DIR, "mp3"))


def remove_file_if_exists(path: str | None) -> None:
    """尽力删除文件，不让文件系统异常影响主流程。"""
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def parse_clip_time(value: str | None) -> float | None:
    """解析截取时间，支持 SS / MM:SS / HH:MM:SS(.ms)。"""
    if value is None:
        return None

    text = value.strip()
    if not text:
        return None

    parts = text.split(":")
    if len(parts) > 3:
        raise ValueError("时间格式不正确，请使用 SS、MM:SS 或 HH:MM:SS")

    if any(not TIME_PART_PATTERN.fullmatch(part) for part in parts):
        raise ValueError("时间格式不正确，请使用数字和冒号")

    if len(parts) == 1:
        seconds = float(parts[0])
        if seconds < 0:
            raise ValueError("时间不能为负数")
        return seconds

    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        if seconds >= 60:
            raise ValueError("秒数必须小于 60")
        return minutes * 60 + seconds

    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    if minutes >= 60 or seconds >= 60:
        raise ValueError("分钟和秒数必须小于 60")
    return hours * 3600 + minutes * 60 + seconds


def validate_clip_range(
    start_time: str | None,
    end_time: str | None,
    source_duration: float | None = None,
) -> tuple[float | None, float | None]:
    """校验截取区间，并在已知源时长时自动收口结束时间。"""
    clip_start = parse_clip_time(start_time)
    clip_end = parse_clip_time(end_time)

    if clip_end is not None and clip_end <= 0:
        raise ValueError("结束时间必须大于 0")

    if source_duration is not None and clip_start is not None and clip_start >= source_duration:
        raise ValueError("开始时间必须小于视频总时长")

    if source_duration is not None and clip_end is not None:
        clip_end = min(clip_end, source_duration)

    if clip_start is not None and clip_end is not None and clip_end <= clip_start:
        raise ValueError("结束时间必须大于开始时间")

    return clip_start, clip_end


def _format_ffmpeg_time(value: float) -> str:
    """把秒数转成 FFmpeg 更稳定接受的 HH:MM:SS.mmm。"""
    total_ms = int(round(value * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


async def _collect_stderr(
    stream: asyncio.StreamReader | None,
    state: dict[str, float | None],
) -> str:
    """持续消费 stderr，避免 ffmpeg 管道写满后阻塞。"""
    if stream is None:
        return ""

    chunks: list[str] = []
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace")
        chunks.append(text)
        if state["duration"] is None:
            state["duration"] = _parse_duration(text)
    return "".join(chunks)


def _parse_duration(stderr_text: str) -> float | None:
    """
    从 ffmpeg stderr 中解析时长。
    示例: Duration: 00:03:45.12, start: 0.000000
    """
    match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d+)", stderr_text)
    if match:
        h, m, s, ms = match.groups()
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / (10 ** len(ms))
    return None


def _parse_time(stderr_text: str) -> float | None:
    """
    从 ffmpeg stderr 中解析当前进度时间。
    示例: time=00:02:15.04
    """
    match = re.search(r"time=\s*(\d{2}):(\d{2}):(\d{2})\.(\d+)", stderr_text)
    if match:
        h, m, s, ms = match.groups()
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / (10 ** len(ms))
    return None


def _resolve_target_duration(
    source_duration: float | None,
    clip_start_seconds: float | None,
    clip_end_seconds: float | None,
) -> float | None:
    clip_start = clip_start_seconds or 0.0
    if clip_end_seconds is not None:
        return max(clip_end_seconds - clip_start, 0.001)
    if source_duration is not None and clip_start_seconds is not None:
        return max(source_duration - clip_start, 0.001)
    return source_duration


async def convert_video_to_mp3(
    task_id: int,
    input_path: str,
    output_path: str,
    bitrate: str = "192k",
    sample_rate: int = 44100,
    channels: int = 2,
    clip_start_seconds: float | None = None,
    clip_end_seconds: float | None = None,
) -> AsyncGenerator[float, None]:
    """
    使用 FFmpeg 将视频转为 MP3，异步迭代进度百分比。

    Yields:
        float: 进度百分比 0.0 ~ 100.0
    """
    ffmpeg = settings.get_ffmpeg_path()

    cmd = [ffmpeg]
    if clip_start_seconds is not None:
        cmd.extend(["-ss", _format_ffmpeg_time(clip_start_seconds)])
    cmd.extend(["-i", input_path])

    target_duration = _resolve_target_duration(None, clip_start_seconds, clip_end_seconds)
    if target_duration is not None:
        cmd.extend(["-t", _format_ffmpeg_time(target_duration)])

    cmd.extend([
        "-vn",                      # 去掉视频流
        "-b:a", bitrate,            # 音频比特率
        "-ar", str(sample_rate),    # 采样率
        "-ac", str(channels),       # 声道数
        "-f", "mp3",                # 强制 mp3 格式
        "-y",                       # 覆盖已存在文件
        "-progress", "pipe:1",      # 进度输出到 stdout（机器可读）
        "-nostats",                 # 不输出统计信息到 stderr
        output_path,
    ])

    # 跨平台: Windows 上需要设置 CREATE_NO_WINDOW 防止弹出控制台窗口。
    # asyncio 的 Unix 子进程实现不支持 creationflags，不能传 None/0。
    subprocess_kwargs = {}
    if os.name == "nt":
        subprocess_kwargs["creationflags"] = getattr(asyncio.subprocess, "CREATE_NO_WINDOW", 0)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **subprocess_kwargs,
    )

    # stdout/stderr 必须并发消费，否则 ffmpeg 任一管道写满都会卡住。
    state: dict[str, float | None] = {"duration": None}
    stderr_task = asyncio.create_task(_collect_stderr(proc.stderr, state))

    # 读取 stdout 进度
    while True:
        if proc.stdout is None:
            break
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace")

        # ffmpeg -progress 输出格式:
        # out_time_ms=123456789
        match = re.search(r"out_time_ms=(\d+)", text)
        duration = _resolve_target_duration(state["duration"], clip_start_seconds, clip_end_seconds)
        if match and duration:
            current_ms = int(match.group(1)) / 1_000_000
            pct = min(round(current_ms / duration * 100, 1), 99.9)
            yield pct

    await proc.wait()
    stderr_full = await stderr_task

    if proc.returncode != 0:
        raise ConversionError(
            f"FFmpeg 返回码 {proc.returncode}: {stderr_full[-500:]}"
        )

    yield 100.0


def get_duration(input_path: str) -> float | None:
    """
    同步获取视频时长（用于创建任务时快速获取元数据）。
    """
    import subprocess
    ffmpeg = settings.get_ffmpeg_path()

    subprocess_kwargs = {}
    if os.name == "nt":
        subprocess_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            [ffmpeg, "-i", input_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            **subprocess_kwargs,
        )
        return _parse_duration(result.stderr)
    except Exception:
        return None


async def create_conversion_task(
    db,
    user_id: int,
    filename: str,
    ext: str,
    file_size: int,
    input_path: str,
    output_path: str,
    bitrate: str = "192k",
    sample_rate: int = 44100,
    channels: int = 2,
    clip_start_seconds: float | None = None,
    clip_end_seconds: float | None = None,
) -> ConversionTask:
    """创建转换任务记录（供 upload 和 convert 路由共用）"""
    task = ConversionTask(
        user_id=user_id,
        original_filename=filename,
        original_format=ext,
        file_size=file_size,
        status="pending",
        input_path=input_path,
        output_path=output_path,
        bitrate=bitrate,
        sample_rate=sample_rate,
        channels=channels,
        clip_start_seconds=clip_start_seconds,
        clip_end_seconds=clip_end_seconds,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task
