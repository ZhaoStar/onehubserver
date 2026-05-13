import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import engine
from app.models.base import Base

settings = get_settings()

# ========== 日志配置 ==========
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
log_format = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 1. 错误日志（ERROR 及以上）→ logs/error.log
error_handler = logging.FileHandler(LOG_DIR / "error.log", encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(log_format)

# # 2. 全量日志（INFO 及以上）→ logs/app.log
# app_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
# app_handler.setLevel(logging.INFO)
# app_handler.setFormatter(log_format)

# # 3. 控制台日志
# console_handler = logging.StreamHandler(sys.stdout)
# console_handler.setLevel(logging.INFO)
# console_handler.setFormatter(log_format)

# 配置根日志器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(error_handler)
# root_logger.addHandler(app_handler)
# root_logger.addHandler(console_handler)

logger = logging.getLogger("onehub")


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


# ========== 请求错误日志中间件 ==========
@app.middleware("http")
async def log_request_errors(request: Request, call_next):
    """捕获所有未处理异常，记录到日志文件"""
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.exception(
            "请求异常 | %s %s | client=%s",
            request.method, request.url.path, request.client.host if request.client else "-",
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请查看日志"},
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
