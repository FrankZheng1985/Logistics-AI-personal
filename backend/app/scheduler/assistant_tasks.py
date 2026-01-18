"""
小助定时任务
- 每日简报推送
- 日程提醒
- 邮件同步
- 明日安排预览
"""
import asyncio
from datetime import datetime, timedelta
from loguru import logger


async def send_daily_briefing():
    """
    每日简报推送
    每天早上8:30推送
    """
    from app.agents.assistant_agent import assistant_agent
    from app.services.assistant_service import assistant_service
    from app.api.wechat_assistant import send_text_message
    
    logger.info("[小助] 开始生成每日简报...")
    
    try:
        # 获取统计数据
        stats = await assistant_service.get_daily_stats()
        today = datetime.now().date()
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]
        
        # 获取今日日程
        schedules = await assistant_service.get_schedules_by_date(today)
        
        # 获取待办事项
        todos = await assistant_service.get_todos(limit=5)
        overdue_todos = await assistant_service.get_overdue_todos()
        
        # 构建简报内容
        lines = [
            f"☀️ 早安！今日简报",
            f"📅 {today.month}月{today.day}日 {weekday}",
            "━" * 18
        ]
        
        # 今日日程
        if schedules:
            lines.append(f"\n📆 今日安排 ({len(schedules)}项)")
            for s in schedules[:5]:
                time_str = datetime.fromisoformat(s["start_time"]).strftime("%H:%M")
                location_str = f" - {s['location']}" if s.get("location") else ""
                lines.append(f"  {time_str} {s['title']}{location_str}")
            if len(schedules) > 5:
                lines.append(f"  ...还有{len(schedules)-5}项")
        else:
            lines.append("\n📆 今日无安排")
        
        # 待办事项
        if todos:
            lines.append(f"\n📋 待办事项 ({len(todos)}项)")
            for t in todos[:3]:
                priority_icon = {"urgent": "🔴", "high": "🟡"}.get(t["priority"], "")
                lines.append(f"  {priority_icon}{t['content'][:20]}")
        
        # 逾期提醒
        if overdue_todos:
            lines.append(f"\n⚠️ 逾期待办 ({len(overdue_todos)}项)")
            for t in overdue_todos[:2]:
                lines.append(f"  • {t['content'][:20]}")
        
        # ERP数据（简化）
        try:
            from app.services.erp_connector import erp_connector
            today_str = datetime.now().strftime("%Y-%m-%d")
            orders = await erp_connector.get_orders(start_date=today_str, end_date=today_str, page_size=1)
            # 昨日数据
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_orders = await erp_connector.get_orders(start_date=yesterday_str, end_date=yesterday_str, page_size=1)
            
            lines.append(f"\n📊 业务数据")
            lines.append(f"  昨日订单: {yesterday_orders.get('total', 0)}单")
        except Exception as e:
            logger.warning(f"获取ERP数据失败: {e}")
        
        # 邮件统计
        try:
            from app.services.multi_email_service import multi_email_service
            email_summary = await multi_email_service.get_unread_summary()
            if email_summary["total_unread"] > 0:
                lines.append(f"\n📧 未读邮件: {email_summary['total_unread']}封")
        except Exception as e:
            logger.warning(f"获取邮件数据失败: {e}")
        
        lines.append("\n━" * 18)
        lines.append("祝您工作顺利！💪")
        
        briefing = "\n".join(lines)
        
        # TODO: 从配置中获取老板的企业微信ID
        # 暂时硬编码或从环境变量获取
        import os
        boss_user_id = os.getenv("ASSISTANT_BOSS_USER_ID", "")
        
        if boss_user_id:
            await send_text_message(boss_user_id, briefing)
            logger.info("[小助] 每日简报已发送")
        else:
            logger.warning("[小助] 未配置老板用户ID，跳过简报发送")
        
    except Exception as e:
        logger.error(f"[小助] 生成每日简报失败: {e}")


async def send_tomorrow_preview():
    """
    明日安排预览
    每天晚上8点推送
    """
    from app.agents.assistant_agent import assistant_agent
    from app.api.wechat_assistant import send_text_message
    import os
    
    logger.info("[小助] 开始生成明日安排预览...")
    
    try:
        boss_user_id = os.getenv("ASSISTANT_BOSS_USER_ID", "")
        
        if not boss_user_id:
            logger.warning("[小助] 未配置老板用户ID，跳过明日预览发送")
            return
        
        # 调用agent的明日预览方法
        preview = await assistant_agent.send_tomorrow_preview(boss_user_id)
        
        if preview:
            await send_text_message(boss_user_id, preview)
            logger.info("[小助] 明日安排预览已发送")
        else:
            logger.info("[小助] 明日无安排，跳过发送")
            
    except Exception as e:
        logger.error(f"[小助] 发送明日预览失败: {e}")


async def check_schedule_reminders():
    """
    检查日程提醒
    每分钟执行一次
    """
    from app.agents.assistant_agent import assistant_agent
    from app.api.wechat_assistant import send_text_message
    import os
    
    try:
        # 获取需要提醒的日程
        reminders = await assistant_agent.get_due_reminders()
        
        if not reminders:
            return
        
        boss_user_id = os.getenv("ASSISTANT_BOSS_USER_ID", "")
        if not boss_user_id:
            return
        
        for reminder in reminders:
            start_time = reminder["start_time"]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
            
            time_str = start_time.strftime("%H:%M")
            location_str = f"\n📍 地点: {reminder['location']}" if reminder.get("location") else ""
            
            message = f"""⏰ 日程提醒

📅 {reminder['title']}
🕐 {time_str}{location_str}

{reminder['minutes_before']}分钟后开始"""
            
            await send_text_message(boss_user_id, message)
            logger.info(f"[小助] 已发送日程提醒: {reminder['title']}")
            
    except Exception as e:
        logger.error(f"[小助] 检查日程提醒失败: {e}")


async def sync_all_emails():
    """
    同步所有邮箱
    每5分钟执行一次
    """
    from app.services.multi_email_service import multi_email_service
    
    logger.info("[小助] 开始同步邮箱...")
    
    try:
        result = await multi_email_service.sync_all_accounts()
        
        total_new = sum(
            r["result"].get("new_count", 0) 
            for r in result["results"] 
            if r["result"].get("success")
        )
        
        if total_new > 0:
            logger.info(f"[小助] 邮箱同步完成，新增 {total_new} 封邮件")
            
            # 检查是否有重要邮件需要提醒
            await check_important_emails()
        else:
            logger.debug("[小助] 邮箱同步完成，无新邮件")
            
    except Exception as e:
        logger.error(f"[小助] 邮箱同步失败: {e}")


async def check_important_emails():
    """
    检查重要邮件并发送提醒
    """
    from app.services.multi_email_service import multi_email_service
    from app.api.wechat_assistant import send_text_message
    import os
    
    # 重要邮件关键词
    IMPORTANT_KEYWORDS = [
        "紧急", "urgent", "重要", "important",
        "报价", "quote", "投诉", "complaint",
        "合同", "contract", "付款", "payment"
    ]
    
    try:
        # 获取最近的未读邮件
        unread_emails = await multi_email_service.get_unread_emails(limit=10)
        
        important_emails = []
        for email in unread_emails:
            subject = (email.get("subject") or "").lower()
            if any(kw in subject for kw in IMPORTANT_KEYWORDS):
                important_emails.append(email)
                # 标记为重要
                await multi_email_service.mark_email_important(email["id"], True)
        
        if not important_emails:
            return
        
        boss_user_id = os.getenv("ASSISTANT_BOSS_USER_ID", "")
        if not boss_user_id:
            return
        
        # 发送提醒
        lines = ["🔔 重要邮件提醒", "━" * 18]
        
        for email in important_emails[:3]:
            sender = email.get("from_name") or email.get("from_address")
            subject = email.get("subject", "无主题")
            lines.append(f"\n📧 {sender}")
            lines.append(f"   {subject[:30]}...")
        
        if len(important_emails) > 3:
            lines.append(f"\n...还有 {len(important_emails)-3} 封重要邮件")
        
        await send_text_message(boss_user_id, "\n".join(lines))
        logger.info(f"[小助] 已发送 {len(important_emails)} 封重要邮件提醒")
        
    except Exception as e:
        logger.error(f"[小助] 检查重要邮件失败: {e}")


async def check_overdue_todos():
    """
    检查逾期待办并提醒
    每天下午2点执行
    """
    from app.services.assistant_service import assistant_service
    from app.api.wechat_assistant import send_text_message
    import os
    
    try:
        overdue_todos = await assistant_service.get_overdue_todos()
        
        if not overdue_todos:
            return
        
        boss_user_id = os.getenv("ASSISTANT_BOSS_USER_ID", "")
        if not boss_user_id:
            return
        
        lines = [
            f"⚠️ 逾期待办提醒",
            "━" * 18,
            f"您有 {len(overdue_todos)} 项待办已逾期：",
            ""
        ]
        
        for t in overdue_todos[:5]:
            due_date = datetime.fromisoformat(t["due_date"]) if t.get("due_date") else None
            due_str = f" (截止{due_date.month}/{due_date.day})" if due_date else ""
            lines.append(f"• {t['content'][:30]}{due_str}")
        
        if len(overdue_todos) > 5:
            lines.append(f"\n...还有 {len(overdue_todos)-5} 项")
        
        lines.append("\n请尽快处理~")
        
        await send_text_message(boss_user_id, "\n".join(lines))
        logger.info(f"[小助] 已发送 {len(overdue_todos)} 项逾期待办提醒")
        
    except Exception as e:
        logger.error(f"[小助] 检查逾期待办失败: {e}")


def register_assistant_tasks(scheduler):
    """
    注册小助定时任务到调度器
    
    Args:
        scheduler: APScheduler实例
    """
    # 每日简报 - 每天早上8:30
    scheduler.add_job(
        send_daily_briefing,
        'cron',
        hour=8,
        minute=30,
        id='assistant_daily_briefing',
        replace_existing=True,
        name='小助每日简报'
    )
    
    # 明日安排预览 - 每天晚上8:00
    scheduler.add_job(
        send_tomorrow_preview,
        'cron',
        hour=20,
        minute=0,
        id='assistant_tomorrow_preview',
        replace_existing=True,
        name='小助明日预览'
    )
    
    # 日程提醒 - 每分钟检查一次
    scheduler.add_job(
        check_schedule_reminders,
        'interval',
        minutes=1,
        id='assistant_schedule_reminders',
        replace_existing=True,
        name='小助日程提醒'
    )
    
    # 邮件同步 - 每5分钟
    scheduler.add_job(
        sync_all_emails,
        'interval',
        minutes=5,
        id='assistant_email_sync',
        replace_existing=True,
        name='小助邮件同步'
    )
    
    # 逾期待办提醒 - 每天下午2点
    scheduler.add_job(
        check_overdue_todos,
        'cron',
        hour=14,
        minute=0,
        id='assistant_overdue_todos',
        replace_existing=True,
        name='小助逾期待办提醒'
    )
    
    logger.info("✓ 小助定时任务已注册")
