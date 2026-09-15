from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.convert import router as convert_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.oil import router as oil_router
from app.api.v1.todos import router as todos_router
from app.api.v1.upload import router as upload_router
from app.api.v1.users import router as users_router
from app.api.v1.weather import router as weather_router

# v1 版本聚合路由
router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(convert_router)
router.include_router(upload_router)
router.include_router(users_router)
router.include_router(oil_router)
router.include_router(weather_router)
router.include_router(todos_router)
router.include_router(notifications_router)

