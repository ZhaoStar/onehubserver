import os
import json
import hmac
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

from fastapi.responses import FileResponse

router = APIRouter(prefix="/app/version", tags=["App版本与在线更新"])

# 存放 APK 与版本信息的静态目录路径
STATIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "static"
APK_DIR = STATIC_DIR / "apk"
VERSION_FILE = APK_DIR / "version.json"

DEFAULT_VERSION_INFO = {
    "versionCode": 2,
    "versionName": "1.1.0",
    "minVersionCode": 1,
    "downloadUrl": "https://api.onehubai.online/api/v1/app/version/download",
    "fileSize": "19.0MB",
    "updateLog": "1. 待办事项支持点击查看详情与直接修改提醒时间\n2. 接入全国及山东油价查询与调价预测模块\n3. 优化真我GT8 64位专属架构 (体积从50MB降至19MB)\n4. 全新极速验证码引擎",
    "publishDate": "2026-09-16 16:20",
    "forceUpdate": False,
}


@router.get("/debug", summary="调试 APK 存放状态")
def debug_apk():
    apk_file = APK_DIR / "onehubapp-latest.apk"
    return {
        "static_dir": str(STATIC_DIR),
        "apk_dir": str(APK_DIR),
        "apk_exists": apk_file.exists(),
        "apk_size": apk_file.stat().st_size if apk_file.exists() else 0,
        "files": [f.name for f in APK_DIR.iterdir()] if APK_DIR.exists() else [],
    }


@router.get("/download", summary="下载最新版 APK 安装包")
def download_latest_apk():
    candidates = [
        APK_DIR / "onehubapp-latest.apk",
        STATIC_DIR / "apk" / "onehubapp-latest.apk",
        Path("/root/onehubserver/static/apk/onehubapp-latest.apk"),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return FileResponse(
                path=str(c),
                filename="onehubapp-latest.apk",
                media_type="application/vnd.android.package-archive",
            )
    raise HTTPException(status_code=404, detail="未找到 APK 文件，请重新上传")


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


from fastapi import UploadFile, File, Form, HTTPException
import time


@router.post("/upload", summary="上传最新 APK 安装包与更新配置")
async def upload_apk(
    file: UploadFile = File(...),
    version_name: Optional[str] = Form(None),
    version_code: Optional[int] = Form(None),
    update_log: Optional[str] = Form(None),
    secret: str = Form(...),
):
    """安全上传最新版 APK 并自动更新 version.json"""
    # 密钥只从 .env 读取：仓库是公开的，明文写死等于把发布接口交给所有人，
    # 需要更换时只改 .env 即可，不用动代码、不用重新发版
    expected = (settings.APK_UPLOAD_SECRET or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="服务端未配置 APK 上传密钥，请在服务器 .env 中设置 APK_UPLOAD_SECRET",
        )
    if not hmac.compare_digest(secret.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=403, detail="上传密钥无效")

    APK_DIR.mkdir(parents=True, exist_ok=True)
    apk_target = APK_DIR / "onehubapp-latest.apk"
    # 边收边写，避免 20MB 安装包整块读进内存；先写临时文件再原子替换，
    # 上传中断也不会把正在分发的线上 APK 弄坏
    tmp_target = APK_DIR / "onehubapp-latest.apk.part"
    total = 0
    with open(tmp_target, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            f.write(chunk)
    os.replace(tmp_target, apk_target)

    size_mb = round(total / (1024 * 1024), 1)

    current_info = _load_version_info()
    if version_name:
        current_info["versionName"] = version_name
    if version_code:
        current_info["versionCode"] = int(version_code)
    if update_log:
        current_info["updateLog"] = update_log
    current_info["fileSize"] = f"{size_mb}MB"
    current_info["publishDate"] = time.strftime("%Y-%m-%d %H:%M")

    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump(current_info, f, ensure_ascii=False, indent=2)

    logger.info(f"成功更新 APK 文件 (大小: {size_mb}MB)")
    return {
        "code": 200,
        "message": "APK 上传并发布成功",
        "data": {
            "fileSize": f"{size_mb}MB",
            "versionName": current_info.get("versionName"),
            "versionCode": current_info.get("versionCode"),
        },
    }
