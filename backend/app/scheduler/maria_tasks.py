"""
Maria 后台智能任务
- 邮件自动同步
- 日历自动同步
- 智能监控与主动提醒
"""
from loguru import logger
from datetime import datetime


async def auto_sync_emails():
    """
    后台自动同步所有邮箱账户的邮件
    每10分钟执行一次，确保邮件缓存始终是最新的
    """
    try:
        from app.services.multi_email_service import multi_email_service
        
        logger.info("[Maria后台] 开始自动同步邮件...")
        
        # 获取所有活跃邮箱账户
        accounts = await multi_email_service.get_email_accounts(active_only=True)
        
        total_new = 0
        for account in accounts:
            try:
                result = await multi_email_service.sync_account_emails(
                    account["id"], 
                    days_back=7, 
                    max_emails=50  # 每次最多同步50封
                )
                
                if result.get("success"):
                    new_count = result.get("new_count", 0)
                    total_new += new_count
                    if new_count > 0:
                        logger.info(f"[Maria后台] {account['name']} 同步了 {new_count} 封新邮件")
                        
            except Exception as e:
                logger.error(f"[Maria后台] 同步 {account['name']} 失败: {e}")
                continue
        
        if total_new > 0:
            logger.info(f"[Maria后台] ✅ 邮件同步完成，共新增 {total_new} 封")
            
            # TODO: 如果有重要邮件，主动通知用户
            # await check_important_emails_and_notify()
        else:
            logger.info(f"[Maria后台] ✅ 邮件同步完成，没有新邮件")
            
    except Exception as e:
        logger.error(f"[Maria后台] 邮件自动同步失败: {e}")


async def auto_sync_calendar():
    """
    后台自动同步日历（暂未实现，预留接口）
    每5分钟执行一次
    """
    try:
        logger.info("[Maria后台] 日历自动同步功能暂未实现，跳过")
        # TODO: 实现日历自动同步
        # from app.services.caldav_service import apple_calendar
        # events = await apple_calendar.query_events(days=7)
        
    except Exception as e:
        logger.error(f"[Maria后台] 日历自动同步失败: {e}")


async def check_important_emails_and_notify():
    """
    检查重要邮件并主动通知用户
    - VIP发件人
    - 包含紧急关键词
    - 大额订单相关
    """
    try:
        from app.services.multi_email_service import multi_email_service
        from app.api.wechat_assistant import send_text_message
        
        # 获取最近10分钟的未读邮件
        summary = await multi_email_service.get_unread_summary()
        
        important_emails = []
        
        for account in summary.get("accounts", []):
            for email in account.get("recent_emails", [])[:5]:  # 只看最新5封
                subject = email.get("subject", "").lower()
                from_addr = email.get("from_address", "").lower()
                
                # 简单的重要性判断规则
                is_important = False
                
                # 规则1：紧急关键词
                urgent_keywords = ["urgent", "紧急", "asap", "重要", "订单", "payment", "付款"]
                if any(kw in subject for kw in urgent_keywords):
                    is_important = True
                
                # 规则2：VIP发件人（可扩展）
                # vip_senders = ["important@example.com"]
                # if any(vip in from_addr for vip in vip_senders):
                #     is_important = True
                
                if is_important:
                    important_emails.append({
                        "subject": email.get("subject"),
                        "from": email.get("from_name") or email.get("from_address"),
                        "account": account.get("name")
                    })
        
        # 如果有重要邮件，发送通知
        if important_emails:
            message = "📬 郑总，您有重要邮件：\n\n"
            for i, email in enumerate(important_emails[:3], 1):  # 最多通知3封
                message += f"{i}. 【{email['account']}】{email['from']}\n"
                message += f"   {email['subject']}\n\n"
            
            # 发送到企业微信
            await send_text_message("Frank.Z", message)
            logger.info(f"[Maria后台] ✅ 已通知用户 {len(important_emails)} 封重要邮件")
            
    except Exception as e:
        logger.error(f"[Maria后台] 检查重要邮件失败: {e}")


async def maria_morning_brief():
    """
    Maria 早间智能简报（每天9:00）
    - 昨日工作总结
    - 今日待办事项
    - 重要提醒
    """
    try:
        from app.api.wechat_assistant import send_text_message
        from app.services.multi_email_service import multi_email_service
        
        logger.info("[Maria后台] 生成早间简报...")
        
        # 获取未读邮件统计
        email_summary = await multi_email_service.get_unread_summary()
        total_unread = email_summary.get("total_unread", 0)
        
        # 构建简报
        brief = f"☀️ 郑总，早上好！\n\n"
        brief += f"📬 未读邮件：{total_unread} 封\n"
        
        if total_unread > 0:
            brief += "\n最新邮件：\n"
            for account in email_summary.get("accounts", [])[:2]:
                if account.get("unread_count", 0) > 0:
                    brief += f"• {account['name']}: {account['unread_count']}封\n"
        
        # TODO: 添加更多信息
        # - 今日日程
        # - 待办任务
        # - 系统状态
        
        brief += "\n祝您今天工作顺利！"
        
        # 发送简报
        await send_text_message("Frank.Z", brief)
        logger.info("[Maria后台] ✅ 早间简报已发送")
        
    except Exception as e:
        logger.error(f"[Maria后台] 早间简报生成失败: {e}")
