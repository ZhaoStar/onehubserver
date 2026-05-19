from fastapi import APIRouter
from app.douyin_api.endpoints import (
    tiktok_web,
    tiktok_app,
    douyin_web,
    bilibili_web,
    hybrid_parsing,
    ios_shortcut,
    download,
)

router = APIRouter()

router.include_router(tiktok_web.router, prefix="/tiktok/web", tags=["TikTok-Web-API"])
router.include_router(tiktok_app.router, prefix="/tiktok/app", tags=["TikTok-App-API"])
router.include_router(douyin_web.router, prefix="/douyin/web", tags=["Douyin-Web-API"])
router.include_router(bilibili_web.router, prefix="/bilibili/web", tags=["Bilibili-Web-API"])
router.include_router(hybrid_parsing.router, prefix="/hybrid", tags=["Hybrid-API"])
router.include_router(ios_shortcut.router, prefix="/ios", tags=["iOS-Shortcut"])
router.include_router(download.router, tags=["Download"])
