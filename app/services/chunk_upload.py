import asyncio
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("onehub")


@dataclass
class UploadSession:
    upload_id: str
    user_id: int
    filename: str
    file_size: int
    total_chunks: int
    chunk_size: int
    ext: str
    temp_dir: str
    chunks_received: set[int] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)

    def all_received(self) -> bool:
        return len(self.chunks_received) == self.total_chunks

    def missing_chunks(self) -> list[int]:
        return sorted(set(range(self.total_chunks)) - self.chunks_received)


class ChunkUploadManager:
    def __init__(self):
        self._sessions: dict[str, UploadSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        user_id: int,
        filename: str,
        file_size: int,
        total_chunks: int,
        chunk_size: int,
    ) -> UploadSession:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        upload_id = uuid.uuid4().hex
        chunks_dir = os.path.join(settings.UPLOAD_DIR, "chunks", upload_id)
        os.makedirs(chunks_dir, exist_ok=True)

        session = UploadSession(
            upload_id=upload_id,
            user_id=user_id,
            filename=filename,
            file_size=file_size,
            total_chunks=total_chunks,
            chunk_size=chunk_size,
            ext=ext,
            temp_dir=chunks_dir,
        )

        async with self._lock:
            self._sessions[upload_id] = session

        logger.info(
            "Upload session created: %s (user=%s, file=%s, chunks=%s, size=%s)",
            upload_id, user_id, filename, total_chunks, file_size,
        )
        return session

    async def get_session(self, upload_id: str, user_id: int) -> UploadSession | None:
        async with self._lock:
            session = self._sessions.get(upload_id)
        if session is None or session.user_id != user_id:
            return None
        return session

    async def add_chunk(
        self, upload_id: str, user_id: int, chunk_index: int, chunk_data: bytes
    ) -> UploadSession | None:
        session = await self.get_session(upload_id, user_id)
        if session is None:
            return None

        chunk_path = os.path.join(session.temp_dir, f"{chunk_index:05d}")
        with open(chunk_path, "wb") as f:
            f.write(chunk_data)

        session.chunks_received.add(chunk_index)
        return session

    async def complete_upload(
        self, upload_id: str, user_id: int
    ) -> tuple[str, int, str] | None:
        """Merge chunks, return (final_path, file_size, original_filename)."""
        session = await self.get_session(upload_id, user_id)
        if session is None:
            return None

        if not session.all_received():
            return None

        input_dir = os.path.join(settings.UPLOAD_DIR, "videos")
        os.makedirs(input_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}.{session.ext}"
        final_path = os.path.join(input_dir, safe_name)

        merged_size = 0
        read_buf_size = 1024 * 1024  # 1MB read buffer for merge
        with open(final_path, "wb") as outfile:
            for i in range(session.total_chunks):
                chunk_path = os.path.join(session.temp_dir, f"{i:05d}")
                with open(chunk_path, "rb") as infile:
                    while True:
                        buf = infile.read(read_buf_size)
                        if not buf:
                            break
                        outfile.write(buf)
                        merged_size += len(buf)

        shutil.rmtree(session.temp_dir, ignore_errors=True)

        async with self._lock:
            self._sessions.pop(upload_id, None)

        logger.info(
            "Upload completed: %s -> %s (merged %s bytes)",
            upload_id, final_path, merged_size,
        )
        return final_path, merged_size, session.filename

    async def cancel_upload(self, upload_id: str, user_id: int) -> None:
        async with self._lock:
            session = self._sessions.pop(upload_id, None)
        if session and session.user_id == user_id:
            shutil.rmtree(session.temp_dir, ignore_errors=True)
            logger.info("Upload cancelled: %s", upload_id)

    async def cleanup_stale_sessions(self, ttl_seconds: int) -> int:
        now = time.time()
        stale_ids: list[str] = []
        async with self._lock:
            for uid, session in self._sessions.items():
                if now - session.created_at > ttl_seconds:
                    stale_ids.append(uid)

        for uid in stale_ids:
            async with self._lock:
                session = self._sessions.pop(uid, None)
            if session:
                shutil.rmtree(session.temp_dir, ignore_errors=True)

        if stale_ids:
            logger.info("Cleaned up %s stale upload sessions", len(stale_ids))
        return len(stale_ids)


_manager: ChunkUploadManager | None = None


def get_chunk_manager() -> ChunkUploadManager:
    global _manager
    if _manager is None:
        _manager = ChunkUploadManager()
    return _manager


async def run_cleanup_loop(
    manager: ChunkUploadManager,
    interval_sec: int,
    ttl_sec: int,
):
    while True:
        await asyncio.sleep(interval_sec)
        try:
            removed = await manager.cleanup_stale_sessions(ttl_sec)
        except Exception:
            logger.exception("Error during upload session cleanup")
