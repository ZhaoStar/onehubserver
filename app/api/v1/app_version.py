import os
import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/app/version", tags=["App版本与在线更新"])

# 存放 APK 与版本信息的静态目录路径
STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "static"
APK_DIR = STATIC_DIR / "apk"
VERSION_FILE = APK_DIR / "version.json"

DEFAULT_VERSION_INFO = {
    "versionCode": 1,
    "versionName": "1.0.0",
    "minVersionCode": 1,
    "downloadUrl": "https://api.onehubai.online/static/apk/onehubapp-latest.apk",
    "fileSize": "30MB",
    "updateLog": "1. 待办事项支持点击查看详情与修改提醒时间\n2. 接入全国及山东油价查询模块\n3. 优化界面交互与视觉质感",
    "publishDate": "2026-09-16",
    "forceUpdate": False,
}


def _load_version_info() -> dict:
    """读取 static/apk/version.json，若不存在则返回默认配置"""
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_VERSION_INFO, **data}
        except Exception as e:
            logger.warning(f"读取 version.json 异常: {e}")
    return dict(DEFAULT_VERSION_INFO)


@router.get("/latest", summary="获取最新移动端版本信息")
async def get_latest_version(
    current_build: Optional[int] = Query(None, description="客户端当前构建编号 versionCode"),
    current_version: Optional[str] = Query(None, description="客户端当前版本名称 versionName"),
    platform: str = Query("android", description="客户端平台 (android/ios)"),
):
    """
    检查 App 是否有更新版本：
    - 若传入 current_build，会自动计算并返回 hasUpdate 字段
    - 支持 forceUpdate（当当前版本低于 minVersionCode 时强制更新）
    """
    version_info = _load_version_info()
    latest_code = int(version_info.get("versionCode", 1))
    min_code = int(version_info.get("minVersionCode", 1))

    has_update = False
    is_force = False

    if current_build is not None:
        has_update = latest_code > current_build
        is_force = current_build < min_code
    elif current_version is not None:
        has_update = current_version != version_info.get("versionName")

    # 如果 APK 文件存在，动态更新实际文件大小
    apk_file = APK_DIR / "onehubapp-latest.apk"
    if apk_file.exists():
        try:
            size_mb = round(apk_file.stat().st_size / (1024 * 1024), 1)
            version_info["fileSize"] = f"{size_mb}MB"
        except Exception:
            pass

    return {
        "code": 200,
        "message": "success",
        "data": {
            **version_info,
            "hasUpdate": has_update,
            "forceUpdate": is_force or version_info.get("forceUpdate", False),
        },
    }
