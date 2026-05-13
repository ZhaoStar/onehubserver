import asyncio
import os
import re
from pathlib import Path
from typing import AsyncGenerator

from app.core.config import get_settings

settings = get_settings()


class ConversionError(Exception):
    """FFmpeg 转换异常"""
    pass


def _ensure_dir(path: str) -> Path:
    """确保目录存在（跨平台）"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_input_dir() -> Path:
    return _ensure_dir(os.path.join(settings.UPLOAD_DIR, "videos"))


def _get_output_dir() -> Path:
    return _ensure_dir(os.path.join(settings.UPLOAD_DIR, "mp3"))


async def _read_stream(stream: asyncio.StreamReader | None) -> str:
    """读取 asyncio 子进程的流"""
    if stream is None:
        return ""
    data = await stream.read()
    return data.decode("utf-8", errors="replace")


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


async def convert_video_to_mp3(
    task_id: int,
    input_path: str,
    output_path: str,
    bitrate: str = "192k",
    sample_rate: int = 44100,
    channels: int = 2,
) -> AsyncGenerator[float, None]:
    """
    使用 FFmpeg 将视频转为 MP3，异步迭代进度百分比。

    Yields:
        float: 进度百分比 0.0 ~ 100.0
    """
    ffmpeg = settings.get_ffmpeg_path()

    cmd = [
        ffmpeg,
        "-i", input_path,          # 输入文件
        "-vn",                      # 去掉视频流
        "-b:a", bitrate,            # 音频比特率
        "-ar", str(sample_rate),    # 采样率
        "-ac", str(channels),       # 声道数
        "-f", "mp3",                # 强制 mp3 格式
        "-y",                       # 覆盖已存在文件
        "-progress", "pipe:1",      # 进度输出到 stdout（机器可读）
        "-nostats",                 # 不输出统计信息到 stderr
        output_path,
    ]

    # 跨平台: Windows 上需要设置 CREATE_NO_WINDOW 防止弹出控制台窗口
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(asyncio.subprocess, "CREATE_NO_WINDOW", 0)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        creationflags=creationflags if creationflags else None,
    )

    # 先读取 stderr 获取视频总时长
    stderr_full = ""
    duration: float | None = None

    while True:
        if proc.stderr is None:
            break
        line = await proc.stderr.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace")
        stderr_full += text
        if duration is None:
            duration = _parse_duration(text)

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
        if match and duration:
            current_ms = int(match.group(1)) / 1_000_000
            pct = min(round(current_ms / duration * 100, 1), 99.9)
            yield pct

    await proc.wait()

    if proc.returncode != 0:
        # 收集剩余 stderr
        remaining = await _read_stream(proc.stderr)
        stderr_full += remaining
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

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            [ffmpeg, "-i", input_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags if creationflags else 0,
            timeout=30,
        )
        return _parse_duration(result.stderr)
    except Exception:
        return None
