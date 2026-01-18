"""
小调定时任务
包括：企业微信日报推送、早间问候等
"""
from loguru import logger
from datetime import datetime


async def coordinator_wechat_daily_report():
    """
    小调 - 企业微信日报推送
    每天下午6点30分自动向管理员发送工作日报
    """
    try:
        logger.info("📊 [小调] 开始企业微信日报推送...")
        
        # 导入发送函数
        from app.api.wechat_coordinator import send_daily_report_to_admins
        
        await send_daily_report_to_admins()
        
        logger.info("✅ [小调] 企业微信日报推送完成")
        
    except Exception as e:
        logger.error(f"❌ [小调] 企业微信日报推送失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def coordinator_wechat_morning_greeting():
    """
    小调 - 企业微信早间问候
    每天早上8点30分向管理员发送今日工作安排提醒
    """
    try:
        logger.info("☀️ [小调] 开始发送早间问候...")
        
        from app.core.config import settings
        from app.api.wechat_coordinator import send_text_message
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        
        admin_users = settings.WECHAT_COORDINATOR_ADMIN_USERS
        if not admin_users:
            logger.info("[小调] 未配置管理员，跳过早间问候")
            return
        
        admin_list = [u.strip() for u in admin_users.split(",") if u.strip()]
        
        # 获取今日待办数据
        async with AsyncSessionLocal() as db:
            # 获取待跟进客户数
            result = await db.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM customers 
                    WHERE next_follow_at <= NOW() + INTERVAL '1 day'
                    AND status NOT IN ('converted', 'lost')
                """)
            )
            pending_follow = result.scalar() or 0
            
            # 获取新线索数
            result = await db.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM leads 
                    WHERE status = 'new'
                    AND created_at >= CURRENT_DATE - INTERVAL '1 day'
                """)
            )
            new_leads = result.scalar() or 0
            
            # 获取昨日完成任务数
            result = await db.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM ai_tasks 
                    WHERE status = 'completed'
                    AND completed_at >= CURRENT_DATE - INTERVAL '1 day'
                """)
            )
            completed_tasks = result.scalar() or 0
        
        today = datetime.now().strftime("%Y年%m月%d日")
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[datetime.now().weekday()]
        
        greeting = f"""☀️ 早上好！今天是 {today} {weekday}

📋 今日工作概览：
• 待跟进客户: {pending_follow} 位
• 新增线索: {new_leads} 条
• 昨日完成任务: {completed_tasks} 项

🤖 AI团队已就绪，随时为您效劳！

💡 回复"日报"查看详细报告
💡 回复"帮助"查看更多指令"""
        
        for user_id in admin_list:
            try:
                await send_text_message([user_id], greeting)
                logger.info(f"[小调] 已向 {user_id} 发送早间问候")
            except Exception as e:
                logger.error(f"[小调] 向 {user_id} 发送早间问候失败: {e}")
        
        logger.info("✅ [小调] 早间问候发送完成")
        
    except Exception as e:
        logger.error(f"❌ [小调] 早间问候发送失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
