# API 路由模块
from fastapi import APIRouter

from app.api import (
    customers, videos, chat, dashboard, agents, 
    wechat, company, leads, follow,
    reports, knowledge, webchat,
    standards, monitoring, marketing,
    assets, settings, notifications, wechat_groups,
    social_auth, erp, wechat_analyst2, content, email,
    topics,  # 热门话题（小猎话题发现模式）
    products,  # 产品趋势（小猎产品发现模式）
    websocket,  # WebSocket实时工作直播
    wechat_eu_monitor,  # 小欧间谍企业微信回调
    wechat_coordinator,  # 小调企业微信回调
    wechat_assistant,  # 小助企业微信回调
    email_accounts  # 多邮箱账户管理
)

router = APIRouter()

# 注册子路由
router.include_router(dashboard.router, prefix="/dashboard", tags=["数据面板"])
router.include_router(customers.router, prefix="/customers", tags=["客户管理"])
router.include_router(leads.router, prefix="/leads", tags=["线索管理"])
router.include_router(follow.router, prefix="/follow", tags=["跟进管理"])
router.include_router(chat.router, prefix="/chat", tags=["对话"])
router.include_router(videos.router, prefix="/videos", tags=["视频"])
router.include_router(agents.router, prefix="/agents", tags=["AI员工"])
router.include_router(wechat.router, tags=["企业微信"])
router.include_router(company.router, tags=["公司配置"])
router.include_router(reports.router)
router.include_router(knowledge.router)
router.include_router(webchat.router)
router.include_router(standards.router, tags=["工作标准"])
router.include_router(monitoring.router, tags=["系统监控"])
router.include_router(marketing.router, prefix="/marketing", tags=["营销序列"])
router.include_router(assets.router, tags=["素材库"])
router.include_router(settings.router, tags=["系统设置"])
router.include_router(notifications.router, tags=["通知中心"])
router.include_router(wechat_groups.router, tags=["微信群监控"])
router.include_router(social_auth.router, tags=["社交媒体登录"])
router.include_router(erp.router, prefix="/erp", tags=["ERP对接"])
router.include_router(wechat_analyst2.router, tags=["企业微信-小析2"])
router.include_router(content.router, prefix="/content", tags=["内容营销"])
router.include_router(email.router, tags=["邮件营销"])
router.include_router(topics.router, prefix="/topics", tags=["热门话题"])
router.include_router(products.router, prefix="/products", tags=["产品趋势"])
router.include_router(websocket.router, tags=["实时工作直播"])
router.include_router(wechat_eu_monitor.router, prefix="/wechat/eu-monitor", tags=["企业微信-小欧间谍"])
router.include_router(wechat_coordinator.router, tags=["企业微信-小调"])
router.include_router(wechat_assistant.router, tags=["企业微信-小助"])
router.include_router(email_accounts.router, tags=["多邮箱管理"])