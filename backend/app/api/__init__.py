# API 路由模块
from fastapi import APIRouter

from app.api import customers, videos, chat, dashboard, agents, wechat

router = APIRouter()

# 注册子路由
router.include_router(dashboard.router, prefix="/dashboard", tags=["数据面板"])
router.include_router(customers.router, prefix="/customers", tags=["客户管理"])
router.include_router(chat.router, prefix="/chat", tags=["对话"])
router.include_router(videos.router, prefix="/videos", tags=["视频"])
router.include_router(agents.router, prefix="/agents", tags=["AI员工"])
router.include_router(wechat.router, tags=["企业微信"])
