from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.convert import router as convert_router
from app.api.v1.upload import router as upload_router

# v1 版本聚合路由
router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(convert_router)
router.include_router(upload_router)
