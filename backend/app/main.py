"""
物流获客AI - FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"📊 调试模式: {settings.DEBUG}")
    
    # 初始化AI员工状态
    logger.info("🤖 AI员工团队上线:")
    logger.info("   - 小调 (调度主管) ✓")
    logger.info("   - 小视 (视频创作) ✓")
    logger.info("   - 小文 (文案策划) ✓")
    logger.info("   - 小销 (销售客服) ✓")
    logger.info("   - 小跟 (跟进专员) ✓")
    logger.info("   - 小析 (客户分析) ✓")
    logger.info("   - 小猎 (线索猎手) ✓")
    
    # 初始化定时任务
    from app.scheduler import init_scheduler, shutdown_scheduler
    await init_scheduler()
    
    yield
    
    # 关闭时执行
    await shutdown_scheduler()
    logger.info("👋 系统关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="物流行业智能获客系统 - AI员工团队",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "ai_team": [
            {"name": "小调", "role": "调度主管", "status": "online"},
            {"name": "小视", "role": "视频创作", "status": "online"},
            {"name": "小文", "role": "文案策划", "status": "online"},
            {"name": "小销", "role": "销售客服", "status": "online"},
            {"name": "小跟", "role": "跟进专员", "status": "online"},
            {"name": "小析", "role": "客户分析", "status": "online"},
            {"name": "小猎", "role": "线索猎手", "status": "online"},
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
