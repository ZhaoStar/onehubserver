from fastapi import APIRouter
from app.api.v1.auth import router as auth_router

# v1 版本聚合路由
router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
