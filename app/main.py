from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import engine
from app.models.base import Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的生命周期"""
    # 启动时：自动建表（仅开发环境，生产请用 alembic）
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # 关闭时：释放连接池
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="OneHub 后端服务",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["健康检查"])
async def root():
    return {"message": f"{settings.APP_NAME} 服务运行中"}


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "ok"}


# 注册路由
from app.api.v1.router import router as v1_router

app.include_router(v1_router)
