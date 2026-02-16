"""
物流获客AI - FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.api import router as api_router


def check_critical_config():
    """
    检查关键配置项，防止使用不安全的默认值
    """
    warnings = []
    errors = []
    
    # 检查 JWT 密钥
    if settings.JWT_SECRET == "your-secret-key-change-in-production":
        if settings.DEBUG:
            warnings.append("⚠️ JWT_SECRET 使用默认值（调试模式允许）")
        else:
            errors.append("❌ 生产环境必须设置 JWT_SECRET 环境变量")
    
    # 检查数据库密码
    if "password@localhost" in settings.DATABASE_URL:
        if settings.DEBUG:
            warnings.append("⚠️ DATABASE_URL 使用默认密码（调试模式允许）")
        else:
            errors.append("❌ 生产环境必须配置安全的数据库密码")
    
    # 检查 AI API 密钥
    if settings.ENABLE_AI:
        if not any([settings.DASHSCOPE_API_KEY, settings.OPENAI_API_KEY, settings.ANTHROPIC_API_KEY]):
            warnings.append("⚠️ 未配置任何 AI API 密钥，AI 功能将不可用")
    else:
        logger.info("ℹ️ 系统处于 AI 禁用模式 (ENABLE_AI=False)")
    
    # 检查加密密钥
    import os
    if not os.getenv("CREDENTIAL_ENCRYPTION_KEY"):
        warnings.append("⚠️ 未配置 CREDENTIAL_ENCRYPTION_KEY，凭证将以明文存储")
    
    # 输出警告和错误
    for warn in warnings:
        logger.warning(warn)
    
    for err in errors:
        logger.error(err)
    
    # 生产环境有错误时退出
    if errors and not settings.DEBUG:
        raise RuntimeError("关键配置缺失，请检查环境变量。详见上方错误信息。")
    
    return len(errors) == 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"📊 调试模式: {settings.DEBUG}")
    
    # 检查关键配置
    check_critical_config()
    
    # 初始化AI员工状态
    logger.info("🤖 AI员工团队上线:")
    logger.info("   - 小调 (调度主管) ✓")
    logger.info("   - 小视 (视频创作) ✓")
    logger.info("   - 小文 (文案策划) ✓")
    logger.info("   - 小销 (销售客服) ✓")
    logger.info("   - 小跟 (跟进专员) ✓")
    logger.info("   - 小析 (客户分析) ✓")
    logger.info("   - 小猎 (线索猎手) ✓")
    logger.info("   - 小析2 (群聊情报员) ✓")
    logger.info("   - 小采 (素材采集员) ✓")
    logger.info("   - 小媒 (内容运营) ✓")
    logger.info("📡 实时工作直播已启用")
    
    # 初始化任务队列
    from app.services.task_queue import task_queue, init_task_handlers
    await task_queue.init()
    await init_task_handlers()
    
    # 初始化智能缓存服务
    from app.services.cache_service import cache_service
    await cache_service.connect()
    
    # 初始化定时任务
    from app.scheduler import init_scheduler, shutdown_scheduler
    await init_scheduler()
    
    # 初始化向量存储服务（Phase 2: RAG）
    try:
        from app.services.vector_store import vector_store
        await vector_store.initialize()
    except Exception as e:
        logger.warning(f"向量存储初始化跳过（RAG功能不可用）: {e}")
    
    # 初始化微信群监控（可选，需要WeChatFerry）
    try:
        from app.services.wechat_monitor import setup_wechat_monitor
        await setup_wechat_monitor()
    except Exception as e:
        logger.warning(f"微信群监控初始化跳过: {e}")
    
    yield
    
    # 关闭时执行
    await task_queue.close()
    await cache_service.close()
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

# CORS中间件（限制允许的方法和头部，增强安全性）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization", 
        "X-Requested-With",
        "Accept",
        "Origin",
        "X-CSRF-Token",
    ],
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
        "ai_enabled": settings.ENABLE_AI,
        "ai_team": [
            {"name": "小调", "role": "调度主管", "status": "online"},
            {"name": "小视", "role": "视频创作", "status": "online"},
            {"name": "小文", "role": "文案策划", "status": "online"},
            {"name": "小销", "role": "销售客服", "status": "online"},
            {"name": "小跟", "role": "跟进专员", "status": "online"},
            {"name": "小析", "role": "客户分析", "status": "online"},
            {"name": "小猎", "role": "线索猎手", "status": "online"},
            {"name": "小析2", "role": "群聊情报员", "status": "online"},
            {"name": "小采", "role": "素材采集员", "status": "online"},
            {"name": "小媒", "role": "内容运营", "status": "online"},
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查 - 返回系统各组件状态"""
    from datetime import datetime
    import time
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "components": {}
    }
    
    # 检查数据库连接
    db_start = time.time()
    try:
        from sqlalchemy import text
        from app.models.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health_status["components"]["database"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - db_start) * 1000, 2)
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # 检查Redis连接
    redis_start = time.time()
    try:
        import redis.asyncio as redis_async
        redis_client = redis_async.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        health_status["components"]["redis"] = {
            "status": "healthy",
            "response_time_ms": round((time.time() - redis_start) * 1000, 2)
        }
    except Exception as e:
        # Redis可选，不影响整体健康状态
        health_status["components"]["redis"] = {
            "status": "unavailable",
            "error": str(e),
            "note": "Redis是可选组件，系统已降级到数据库模式"
        }
    
    # 检查任务队列
    try:
        from app.services.task_queue import task_queue
        queue_stats = await task_queue.get_queue_stats()
        health_status["components"]["task_queue"] = {
            "status": "healthy",
            "mode": "redis" if task_queue._redis else "database",
            "stats": queue_stats
        }
    except Exception as e:
        health_status["components"]["task_queue"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # 检查定时任务调度器
    try:
        from app.scheduler import scheduler
        if scheduler and scheduler.running:
            jobs = scheduler.get_jobs()
            health_status["components"]["scheduler"] = {
                "status": "healthy",
                "running": True,
                "job_count": len(jobs)
            }
        else:
            health_status["components"]["scheduler"] = {
                "status": "disabled",
                "running": False
            }
    except Exception as e:
        health_status["components"]["scheduler"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # 检查AI API可用性（仅检查配置，不实际调用）
    ai_apis = {}
    if settings.DASHSCOPE_API_KEY:
        ai_apis["dashscope"] = "configured"
    if settings.OPENAI_API_KEY:
        ai_apis["openai"] = "configured"
    if settings.ANTHROPIC_API_KEY:
        ai_apis["anthropic"] = "configured"
    if settings.KELING_ACCESS_KEY:
        ai_apis["keling"] = "configured"
    
    health_status["components"]["ai_apis"] = {
        "status": "healthy" if ai_apis else "unconfigured",
        "providers": ai_apis
    }
    
    return health_status
