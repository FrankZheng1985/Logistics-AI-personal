"""
Maria 后台智能任务
- 邮件自动同步
- 日历自动同步
- 智能监控与主动提醒
- 邮件上下文记忆
- 主动任务巡检与进度汇报（新增）
"""
from loguru import logger
from datetime import datetime, timedelta
from app.services.email_context_service import email_context_service


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
            
            # 检查是否有重要邮件，主动通知用户
            try:
                await check_important_emails_and_notify()
            except Exception as notify_err:
                logger.warning(f"[Maria后台] 重要邮件检查失败: {notify_err}")
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


# 已通知邮件缓存（避免重复提醒）
# 格式: {邮件唯一标识: 通知时间}
_notified_emails_cache = {}
_NOTIFIED_CACHE_MAX_SIZE = 500  # 最多缓存500条
_NOTIFIED_CACHE_EXPIRE_HOURS = 24  # 24小时后过期可重新提醒

# ========== 用户忽略的邮件列表（持久化到Redis） ==========
IGNORED_EMAILS_REDIS_KEY = "maria:ignored_emails"


async def _get_ignored_emails() -> set:
    """从Redis获取用户忽略的邮件列表"""
    try:
        from app.services.cache_service import cache_service
        data = await cache_service.get(IGNORED_EMAILS_REDIS_KEY)
        if data:
            return set(data) if isinstance(data, list) else set()
    except Exception as e:
        logger.warning(f"[邮件忽略] 读取忽略列表失败: {e}")
    return set()


async def _add_ignored_email(email_identifier: str) -> bool:
    """将邮件加入忽略列表（永久忽略）
    
    email_identifier 可以是：
    - 邮件主题（模糊匹配）
    - 发件人邮箱
    - 完整邮件ID
    """
    try:
        from app.services.cache_service import cache_service
        ignored = await _get_ignored_emails()
        ignored.add(email_identifier.lower().strip())
        # 持久化到 Redis，不设过期时间（永久忽略）
        await cache_service.set(IGNORED_EMAILS_REDIS_KEY, list(ignored), ttl=None)
        logger.info(f"[邮件忽略] 已添加忽略: {email_identifier}")
        return True
    except Exception as e:
        logger.error(f"[邮件忽略] 添加失败: {e}")
        return False


async def _is_email_ignored(email: dict, account_name: str) -> bool:
    """检查邮件是否在忽略列表中"""
    try:
        ignored = await _get_ignored_emails()
        if not ignored:
            return False
        
        subject = (email.get("subject", "") or "").lower()
        from_addr = (email.get("from_address", "") or "").lower()
        
        for pattern in ignored:
            # 匹配主题（包含关键词即忽略）
            if pattern in subject:
                return True
            # 匹配发件人
            if pattern in from_addr:
                return True
        
        return False
    except Exception as e:
        logger.warning(f"[邮件忽略] 检查失败: {e}")
        return False


async def ignore_email_by_user(identifier: str) -> dict:
    """用户明确要求忽略某封邮件/某类邮件
    
    这是 Maria 调用的接口，当用户说"不处理"、"已读"、"过滤"时调用
    
    Args:
        identifier: 邮件主题关键词、发件人邮箱等
    
    Returns:
        {"success": True/False, "message": "..."}
    """
    success = await _add_ignored_email(identifier)
    if success:
        return {
            "success": True,
            "message": f"好的，已将包含「{identifier}」的邮件加入忽略列表，以后不会再提醒您。"
        }
    else:
        return {
            "success": False,
            "message": "抱歉，添加忽略失败，请稍后再试。"
        }


def _get_email_id(email: dict, account_name: str) -> str:
    """生成邮件唯一标识"""
    subject = email.get("subject", "")[:50]
    from_addr = email.get("from_address", "")
    date_str = str(email.get("received_at", ""))[:10]  # 只取日期部分
    return f"{account_name}:{from_addr}:{subject}:{date_str}"


def _is_email_notified(email_id: str) -> bool:
    """检查邮件是否已通知过（24小时内）"""
    from datetime import datetime, timedelta
    
    if email_id not in _notified_emails_cache:
        return False
    
    notified_time = _notified_emails_cache[email_id]
    # 超过24小时可以重新提醒
    if datetime.now() - notified_time > timedelta(hours=_NOTIFIED_CACHE_EXPIRE_HOURS):
        del _notified_emails_cache[email_id]
        return False
    
    return True


def _mark_email_notified(email_id: str):
    """标记邮件已通知"""
    from datetime import datetime
    
    # 清理过期缓存
    if len(_notified_emails_cache) > _NOTIFIED_CACHE_MAX_SIZE:
        # 删除最旧的一半
        sorted_items = sorted(_notified_emails_cache.items(), key=lambda x: x[1])
        for key, _ in sorted_items[:len(sorted_items)//2]:
            del _notified_emails_cache[key]
    
    _notified_emails_cache[email_id] = datetime.now()


async def check_important_emails_and_notify():
    """
    检查重要邮件并主动通知用户（增强版）
    - VIP发件人（可配置）
    - 包含紧急关键词
    - 大额订单相关
    - 回复/转发的邮件
    - 客户域名邮件
    
    注意：已通知过的邮件24小时内不会重复提醒
    """
    try:
        from app.services.multi_email_service import multi_email_service
        from app.api.wechat_assistant import send_text_message
        
        # 获取未读邮件摘要
        summary = await multi_email_service.get_unread_summary()
        
        # 紧急关键词（主题和正文）
        URGENT_KEYWORDS = [
            # 英文
            "urgent", "asap", "important", "critical", "emergency", "deadline",
            "payment", "invoice", "order", "shipping", "delivery", "tracking",
            "quote", "quotation", "inquiry", "rfq", "po ", "purchase order",
            "customs", "clearance", "delay",
            # 中文
            "紧急", "重要", "急", "订单", "付款", "发票", "报价", "询盘",
            "货运", "物流", "清关", "海关", "延误", "催", "尽快",
        ]
        
        # VIP发件人域名（可扩展）
        VIP_DOMAINS = [
            # 大客户域名
            "amazon.com", "alibaba.com", "dhl.com", "fedex.com", "ups.com",
        ]
        
        important_emails = []
        
        for account in summary.get("accounts", []):
            for email in account.get("recent_emails", [])[:10]:  # 检查最新10封
                subject = (email.get("subject", "") or "").lower()
                from_addr = (email.get("from_address", "") or "").lower()
                body_preview = (email.get("body_preview", "") or "").lower()
                
                is_important = False
                reason = ""
                
                # 规则1：紧急关键词（主题优先）
                for kw in URGENT_KEYWORDS:
                    if kw in subject:
                        is_important = True
                        reason = f"主题含「{kw}」"
                        break
                    if kw in body_preview:
                        is_important = True
                        reason = f"正文含「{kw}」"
                        break
                
                # 规则2：VIP发件人域名
                if not is_important:
                    for domain in VIP_DOMAINS:
                        if domain in from_addr:
                            is_important = True
                            reason = f"来自 {domain}"
                            break
                
                # 规则3：回复邮件（可能是客户回复）
                if not is_important and (subject.startswith("re:") or subject.startswith("回复:")):
                    is_important = True
                    reason = "客户回复"
                
                if is_important:
                    # 检查是否在用户忽略列表中（永久忽略）
                    if await _is_email_ignored(email, account.get("name", "")):
                        continue  # 用户已明确说不处理，永久跳过
                    
                    # 检查是否已通知过（24小时内避免重复提醒）
                    email_id = _get_email_id(email, account.get("name", ""))
                    if _is_email_notified(email_id):
                        continue  # 跳过已通知的邮件
                    
                    important_emails.append({
                        "subject": email.get("subject", "(无主题)"),
                        "from": email.get("from_name") or email.get("from_address"),
                        "account": account.get("name"),
                        "reason": reason,
                        "preview": (email.get("body_preview", "") or "")[:60],
                        "_email_id": email_id,  # 保存ID用于标记
                    })
        
        # 去重（同一主题只保留一封）
        seen_subjects = set()
        unique_emails = []
        for e in important_emails:
            subj_key = e["subject"][:30].lower()
            if subj_key not in seen_subjects:
                seen_subjects.add(subj_key)
                unique_emails.append(e)
        
        # 如果有重要邮件，发送通知
        if unique_emails:
            message = f"📬 郑总，您有 {len(unique_emails)} 封重要邮件：\n\n"
            for i, email in enumerate(unique_emails[:5], 1):  # 最多通知5封
                message += f"{i}. 【{email['account']}】{email['from']}\n"
                message += f"   📌 {email['subject'][:40]}\n"
                if email.get("preview"):
                    message += f"   💬 {email['preview']}...\n"
                message += f"   🔖 {email['reason']}\n\n"
            
            if len(unique_emails) > 5:
                message += f"还有 {len(unique_emails) - 5} 封，请查看邮箱。\n"
            
            message += "需要我帮您处理或回复吗？"
            
            # 发送到企业微信
            await send_text_message("Frank.Z", message)
            
            # 标记这些邮件为已通知（避免重复提醒）
            for email in unique_emails:
                if "_email_id" in email:
                    _mark_email_notified(email["_email_id"])
            
            logger.info(f"[Maria后台] ✅ 已通知用户 {len(unique_emails)} 封重要邮件")
            
    except Exception as e:
        import traceback
        logger.error(f"[Maria后台] 检查重要邮件失败: {e}")
        logger.error(traceback.format_exc())


async def maria_morning_brief():
    """
    Maria 早间智能简报（每天9:00）
    
    包含：
    1. 今日日程概览 + 冲突检测
    2. AI团队任务进度（进行中/待处理）
    3. 未读邮件统计
    4. 主动建议（基于日程和任务分析）
    """
    try:
        from app.api.wechat_assistant import send_text_message
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        import pytz
        
        logger.info("[Maria后台] 生成早间智能简报...")
        
        CHINA_TZ = pytz.timezone('Asia/Shanghai')
        now = datetime.now(CHINA_TZ)
        today_str = now.strftime("%Y-%m-%d")
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[now.weekday()]
        
        brief_parts = [f"郑总，早上好！今天是{now.month}月{now.day}日 {weekday}。\n"]
        suggestions = []  # 主动建议收集
        
        # ===== 1. 今日日程 + 冲突检测 =====
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT title, start_time, end_time, location, priority
                        FROM assistant_schedules
                        WHERE DATE(start_time) = :today
                        AND is_completed = FALSE
                        ORDER BY start_time ASC
                    """),
                    {"today": today_str}
                )
                schedules = result.fetchall()
            
            if schedules:
                brief_parts.append(f"今日日程（{len(schedules)}项）：")
                
                prev_end = None
                for s in schedules:
                    title, start, end_time, location, priority = s[0], s[1], s[2], s[3], s[4]
                    
                    if start and start.tzinfo is None:
                        start = pytz.UTC.localize(start)
                    china_start = start.astimezone(CHINA_TZ) if start else None
                    
                    time_str = china_start.strftime("%H:%M") if china_start else "全天"
                    loc_str = f" - {location}" if location else ""
                    priority_icon = {"urgent": "!!", "high": "!"}.get(priority, "")
                    
                    brief_parts.append(f"  {time_str} {priority_icon}{title}{loc_str}")
                    
                    # 冲突检测：当前日程开始时间早于上一个日程结束时间
                    if prev_end and china_start and china_start < prev_end:
                        suggestions.append(f"日程冲突：「{title}」与前一个日程时间重叠，建议调整")
                    
                    if end_time:
                        if end_time.tzinfo is None:
                            end_time = pytz.UTC.localize(end_time)
                        prev_end = end_time.astimezone(CHINA_TZ)
                    elif china_start:
                        # 默认假设1小时
                        from datetime import timedelta
                        prev_end = china_start + timedelta(hours=1)
                
                brief_parts.append("")
            else:
                brief_parts.append("今天没有日程安排，可以专注处理项目。\n")
        except Exception as e:
            logger.warning(f"[Maria简报] 日程查询失败: {e}")
        
        # ===== 2. AI团队任务进度 =====
        try:
            async with AsyncSessionLocal() as db:
                # 进行中的任务
                result = await db.execute(
                    text("""
                        SELECT agent_type, COUNT(*) 
                        FROM ai_tasks 
                        WHERE status = 'pending' 
                        GROUP BY agent_type
                    """)
                )
                pending_tasks = result.fetchall()
                
                # 昨日完成的任务
                result2 = await db.execute(
                    text("""
                        SELECT COUNT(*) FROM ai_tasks 
                        WHERE status = 'completed' 
                        AND completed_at >= CURRENT_DATE - INTERVAL '1 day'
                        AND completed_at < CURRENT_DATE
                    """)
                )
                yesterday_completed = result2.fetchone()[0]
                
                # 失败的任务
                result3 = await db.execute(
                    text("""
                        SELECT COUNT(*) FROM ai_tasks 
                        WHERE status = 'failed' 
                        AND created_at >= CURRENT_DATE - INTERVAL '1 day'
                    """)
                )
                recent_failed = result3.fetchone()[0]
            
            agent_names = {
                "coordinator": "小调", "video_creator": "小影",
                "copywriter": "小文", "sales": "小销",
                "follow": "小跟", "analyst": "小析",
                "lead_hunter": "小猎", "analyst2": "小析2",
                "eu_customs_monitor": "小欧间谍",
            }
            
            if pending_tasks:
                total_pending = sum(row[1] for row in pending_tasks)
                brief_parts.append(f"AI团队：{total_pending}个任务待处理")
                for row in pending_tasks:
                    name = agent_names.get(row[0], row[0])
                    brief_parts.append(f"  {name}: {row[1]}个")
                brief_parts.append("")
                
                if total_pending > 10:
                    suggestions.append(f"任务积压：当前有{total_pending}个待处理任务，建议关注队列消化速度")
            
            if yesterday_completed > 0:
                brief_parts.append(f"昨日完成：{yesterday_completed}个任务")
            
            if recent_failed > 0:
                brief_parts.append(f"近期失败：{recent_failed}个任务")
                suggestions.append(f"有{recent_failed}个任务执行失败，建议查看原因")
            
            brief_parts.append("")
        except Exception as e:
            logger.warning(f"[Maria简报] 任务统计失败: {e}")
        
        # ===== 3. 未读邮件 =====
        try:
            from app.services.multi_email_service import multi_email_service
            email_summary = await multi_email_service.get_unread_summary()
            total_unread = email_summary.get("total_unread", 0)
            
            if total_unread > 0:
                brief_parts.append(f"未读邮件：{total_unread}封")
                for account in email_summary.get("accounts", [])[:3]:
                    if account.get("unread_count", 0) > 0:
                        brief_parts.append(f"  {account['name']}: {account['unread_count']}封")
                brief_parts.append("")
                
                if total_unread > 20:
                    suggestions.append(f"邮箱积压：{total_unread}封未读邮件，建议抽空处理")
            else:
                brief_parts.append("邮箱清净，没有未读邮件。\n")
        except Exception as e:
            logger.warning(f"[Maria简报] 邮件统计失败: {e}")
        
        # ===== 4. 主动建议 =====
        if suggestions:
            brief_parts.append("我的建议：")
            for i, s in enumerate(suggestions, 1):
                brief_parts.append(f"  {i}. {s}")
            brief_parts.append("")
        
        brief_parts.append("有需要随时叫我。")
        
        # 发送简报
        brief = "\n".join(brief_parts)
        await send_text_message("Frank.Z", brief)
        logger.info("[Maria后台] 早间智能简报已发送")
        
    except Exception as e:
        logger.error(f"[Maria后台] 早间简报生成失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def check_maria_inbox_attachments():
    """
    检查 Maria 专属邮箱中带附件的邮件
    自动下载附件并分析内容，通知老板
    
    每10分钟执行一次
    """
    try:
        from app.services.multi_email_service import multi_email_service
        from app.api.wechat_assistant import send_text_message
        from app.services.document_service import document_service
        from app.core.llm import chat_completion
        
        logger.info("[Maria邮箱] 检查收件箱附件...")
        
        # 获取 Maria 邮箱最近24小时的未读邮件
        emails = await multi_email_service.get_maria_inbox_emails(
            hours=24,
            unread_only=True
        )
        
        if not emails:
            logger.debug("[Maria邮箱] 没有新邮件")
            return
        
        # 筛选带附件的邮件
        emails_with_attachments = [e for e in emails if e.get("has_attachments")]
        
        if not emails_with_attachments:
            logger.debug("[Maria邮箱] 没有带附件的新邮件")
            return
        
        logger.info(f"[Maria邮箱] 发现 {len(emails_with_attachments)} 封带附件的邮件")
        
        for email in emails_with_attachments:
            try:
                email_id = email["id"]
                subject = email.get("subject", "(无主题)")
                from_name = email.get("from_name") or email.get("from_address", "未知发件人")
                attachment_names = email.get("attachment_names", [])
                
                # 先通知收到邮件
                await send_text_message(
                    "Frank.Z",
                    f"📧 收到一封带附件的邮件：\n\n"
                    f"📌 主题：{subject}\n"
                    f"👤 发件人：{from_name}\n"
                    f"📎 附件：{', '.join(attachment_names)}\n\n"
                    f"正在下载并分析..."
                )
                
                # 下载附件
                download_result = await multi_email_service.download_attachments(
                    email_id,
                    save_dir="/tmp/maria_attachments"
                )
                
                if not download_result.get("success"):
                    await send_text_message(
                        "Frank.Z",
                        f"⚠️ 附件下载失败：{download_result.get('error', '未知错误')}"
                    )
                    continue
                
                attachments = download_result.get("attachments", [])
                
                # 分析每个附件
                for att in attachments:
                    filename = att.get("filename", "未知文件")
                    filepath = att.get("path")
                    content_type = att.get("content_type", "")
                    
                    # 只分析文档类型
                    supported_types = [
                        "application/pdf", "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "text/plain"
                    ]
                    
                    if content_type not in supported_types and not filename.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
                        await send_text_message(
                            "Frank.Z",
                            f"📎 附件「{filename}」不是文档类型，暂不支持分析。"
                        )
                        continue
                    
                    # 读取文档内容
                    doc_result = await document_service.read_document(filepath, filename)
                    
                    if not doc_result.get("success"):
                        await send_text_message(
                            "Frank.Z",
                            f"⚠️ 无法读取「{filename}」：{doc_result.get('error', '格式不支持')}"
                        )
                        continue
                    
                    content = doc_result.get("content", "")
                    word_count = len(content)
                    
                    if word_count < 50:
                        await send_text_message(
                            "Frank.Z",
                            f"📎 附件「{filename}」内容过少（{word_count}字），跳过分析。"
                        )
                        continue
                    
                    # 判断文档类型并构建分析提示词
                    filename_lower = filename.lower()
                    is_contract = any(kw in filename_lower for kw in ["合同", "协议", "contract", "agreement"])
                    is_finance = any(kw in filename_lower for kw in ["发票", "invoice", "财务", "报表", "账单"])
                    is_logistics = any(kw in filename_lower for kw in ["运输", "物流", "logistics", "shipping", "提单", "报关"])
                    
                    if is_contract:
                        prompt = f"""【法律顾问模式】老板通过邮件发来一份合同/协议，请以资深法务的身份进行专业分析：

📄 文件名：{filename}
📧 来自：{from_name}
📌 邮件主题：{subject}

📝 文档内容：
{content[:15000]}

---
请分析：
1. 合同类型和主要条款
2. 对我方的主要权利和义务
3. 潜在风险点（红旗条款）
4. 建议的修改或谈判要点
5. 总体评估（是否建议签署）"""
                    elif is_finance:
                        prompt = f"""【财务分析模式】老板通过邮件发来一份财务文档，请以专业会计的身份进行分析：

📄 文件名：{filename}
📧 来自：{from_name}
📌 邮件主题：{subject}

📝 文档内容：
{content[:15000]}

---
请分析：
1. 文档类型和主要内容
2. 关键数据摘要
3. 需要注意的事项
4. 建议的处理方式"""
                    elif is_logistics:
                        prompt = f"""【跨境贸易专家模式】老板通过邮件发来一份物流/贸易文档，请以国际贸易专家的身份分析：

📄 文件名：{filename}
📧 来自：{from_name}
📌 邮件主题：{subject}

📝 文档内容：
{content[:15000]}

---
请分析：
1. 文档类型和关键信息
2. 运输/贸易条款分析
3. 潜在风险和注意事项
4. 后续需要跟进的事项"""
                    else:
                        prompt = f"""老板通过邮件发来一份文档，请帮忙阅读并分析：

📄 文件名：{filename}
📧 来自：{from_name}
📌 邮件主题：{subject}

📝 文档内容：
{content[:15000]}

---
请分析：
1. 文档的主要内容和目的
2. 关键信息摘要
3. 需要老板关注或决策的事项
4. 建议的处理方式"""
                    
                    # 调用 LLM 分析（成本优化：优先便宜模型）
                    import asyncio
                    
                    # 根据文档类型选择最优模型（优先便宜的）
                    if is_contract:
                        model_preference = "legal"  # 法律分析 → DeepSeek（便宜够用）
                    elif is_finance:
                        model_preference = "finance"  # 财务分析 → DeepSeek
                    elif is_logistics:
                        model_preference = "reasoning"  # 物流分析 → DeepSeek
                    else:
                        model_preference = None  # 通用任务 → Qwen-Max（最便宜）
                    
                    try:
                        response = await asyncio.wait_for(
                            chat_completion(
                                messages=[{"role": "user", "content": prompt}],
                                model_preference=model_preference,  # 博士后级智能路由
                                use_advanced=True  # 备用：高级模型
                            ),
                            timeout=120  # 2分钟超时
                        )
                        
                        # 处理返回结果（可能是字符串或字典）
                        if isinstance(response, str):
                            analysis = response
                        elif isinstance(response, dict):
                            analysis = response.get("content", str(response))
                        else:
                            analysis = str(response)
                        
                        # 发送分析结果
                        await send_text_message(
                            "Frank.Z",
                            f"📄 **{filename}** 分析完成（{word_count}字）\n\n{analysis}"
                        )
                        
                        # 保存邮件上下文（让Maria记住这封邮件，以便用户后续引用）
                        doc_type_map = {
                            True: "contract",  # is_contract
                        }
                        if is_contract:
                            saved_doc_type = "contract"
                        elif is_finance:
                            saved_doc_type = "invoice"
                        elif is_logistics:
                            saved_doc_type = "logistics"
                        else:
                            saved_doc_type = "general"
                        
                        await email_context_service.save_email_context(
                            user_id="Frank.Z",  # 默认老板ID
                            email_id=email_id,
                            subject=subject,
                            from_address=from_addr,
                            from_name=from_name,
                            attachment_name=filename,
                            attachment_content=content,
                            analysis_result=analysis,
                            doc_type=saved_doc_type
                        )
                        logger.info(f"[Maria邮箱] 已保存邮件上下文: {filename} (type={saved_doc_type})")
                        
                    except asyncio.TimeoutError:
                        await send_text_message(
                            "Frank.Z",
                            f"⚠️ 分析「{filename}」超时，文档可能太长。您可以直接回复让我重试。"
                        )
                    except Exception as llm_err:
                        logger.error(f"[Maria邮箱] LLM 分析失败: {llm_err}")
                        await send_text_message(
                            "Frank.Z",
                            f"⚠️ 分析「{filename}」时出错：{str(llm_err)[:100]}"
                        )
                
                # 标记邮件已读
                await multi_email_service.mark_email_read(email_id)
                
            except Exception as email_err:
                logger.error(f"[Maria邮箱] 处理邮件失败: {email_err}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"[Maria邮箱] 处理完成")
        
    except Exception as e:
        logger.error(f"[Maria邮箱] 检查附件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def maria_proactive_task_check():
    """
    Maria 主动任务巡检（每2小时执行一次）
    
    功能：
    1. 检查AI团队任务积压情况
    2. 检查长时间未完成的任务
    3. 检查失败率异常的员工
    4. 主动向老板汇报问题和建议
    """
    try:
        from app.api.wechat_assistant import send_text_message
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        import pytz
        
        logger.info("[Maria巡检] 开始主动任务巡检...")
        
        CHINA_TZ = pytz.timezone('Asia/Shanghai')
        now = datetime.now(CHINA_TZ)
        
        issues = []  # 发现的问题
        suggestions = []  # 建议
        
        agent_names = {
            "coordinator": "小调", "video_creator": "小影",
            "copywriter": "小文", "sales": "小销",
            "follow": "小跟", "analyst": "小析",
            "lead_hunter": "小猎", "analyst2": "小析2",
            "eu_customs_monitor": "小欧间谍",
        }
        
        async with AsyncSessionLocal() as db:
            # ===== 1. 检查任务积压 =====
            result = await db.execute(
                text("""
                    SELECT agent_type, COUNT(*) as cnt
                    FROM ai_tasks 
                    WHERE status = 'pending' 
                    GROUP BY agent_type
                    HAVING COUNT(*) > 5
                """)
            )
            backlog = result.fetchall()
            
            for row in backlog:
                agent_type, count = row[0], row[1]
                agent_name = agent_names.get(agent_type, agent_type)
                issues.append(f"{agent_name} 有 {count} 个任务积压")
            
            # ===== 2. 检查长时间未完成的任务（超过24小时） =====
            result = await db.execute(
                text("""
                    SELECT agent_type, task_description, created_at
                    FROM ai_tasks 
                    WHERE status = 'pending'
                    AND created_at < NOW() - INTERVAL '24 hours'
                    ORDER BY created_at ASC
                    LIMIT 5
                """)
            )
            stale_tasks = result.fetchall()
            
            if stale_tasks:
                issues.append(f"有 {len(stale_tasks)} 个任务超过24小时未完成")
                for task in stale_tasks[:3]:
                    agent_name = agent_names.get(task[0], task[0])
                    desc = (task[1] or "")[:30]
                    issues.append(f"  - {agent_name}: {desc}...")
            
            # ===== 3. 检查最近24小时失败率 =====
            result = await db.execute(
                text("""
                    SELECT agent_type,
                           COUNT(*) FILTER (WHERE status = 'failed') as failed,
                           COUNT(*) as total
                    FROM ai_tasks 
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY agent_type
                    HAVING COUNT(*) > 3 AND COUNT(*) FILTER (WHERE status = 'failed') > 0
                """)
            )
            failure_stats = result.fetchall()
            
            for row in failure_stats:
                agent_type, failed, total = row[0], row[1], row[2]
                failure_rate = (failed / total) * 100
                if failure_rate > 30:  # 失败率超过30%
                    agent_name = agent_names.get(agent_type, agent_type)
                    issues.append(f"{agent_name} 失败率 {failure_rate:.0f}%（{failed}/{total}个任务）")
                    suggestions.append(f"建议检查 {agent_name} 的配置或日志")
            
            # ===== 3.5. 显示最近失败任务的详细信息（新增） =====
            result = await db.execute(
                text("""
                    SELECT 
                        agent_type,
                        task_description,
                        error_message,
                        completed_at,
                        id
                    FROM ai_tasks 
                    WHERE status = 'failed'
                    AND completed_at > NOW() - INTERVAL '6 hours'
                    ORDER BY completed_at DESC
                    LIMIT 5
                """)
            )
            recent_failures = result.fetchall()
            
            if recent_failures:
                issues.append(f"\n⚠️ 最近6小时失败的任务详情：")
                for task in recent_failures:
                    agent_type, desc, error, completed_at, task_id = task
                    agent_name = agent_names.get(agent_type, agent_type)
                    desc_short = (desc or "未知任务")[:40]
                    error_short = (error or "未知错误")[:60]
                    time_str = completed_at.strftime("%H:%M") if completed_at else "?"
                    issues.append(f"  [{time_str}] {agent_name}: {desc_short}")
                    issues.append(f"      ❌ 原因: {error_short}")
                
                suggestions.append("可以让我重试失败的任务，或者检查系统日志")
            
            # ===== 4. 检查今日待办完成情况 =====
            result = await db.execute(
                text("""
                    SELECT COUNT(*) as pending
                    FROM assistant_schedules
                    WHERE DATE(start_time) = CURRENT_DATE
                    AND is_completed = FALSE
                """)
            )
            pending_schedules = result.fetchone()[0]
            
            if pending_schedules > 0 and now.hour >= 17:  # 下午5点后还有未完成的日程
                issues.append(f"今日还有 {pending_schedules} 个日程/待办未完成")
        
        # ===== 5. 如果有问题，主动汇报 =====
        if issues:
            message = f"郑总，Maria 主动巡检发现以下问题：\n\n"
            
            for i, issue in enumerate(issues, 1):
                message += f"{i}. {issue}\n"
            
            if suggestions:
                message += "\n我的建议：\n"
                for s in suggestions:
                    message += f"• {s}\n"
            
            message += "\n需要我处理哪个问题吗？"
            
            await send_text_message("Frank.Z", message)
            logger.info(f"[Maria巡检] 已主动汇报 {len(issues)} 个问题")
        else:
            logger.info("[Maria巡检] 一切正常，无需汇报")
        
    except Exception as e:
        logger.error(f"[Maria巡检] 主动巡检失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def maria_evening_summary():
    """
    Maria 晚间工作总结（每天18:30执行）
    
    功能：
    1. 今日任务完成统计
    2. 今日邮件处理情况
    3. 明日待办提醒
    4. AI团队工作成果
    """
    try:
        from app.api.wechat_assistant import send_text_message
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        import pytz
        
        logger.info("[Maria晚报] 生成晚间工作总结...")
        
        CHINA_TZ = pytz.timezone('Asia/Shanghai')
        now = datetime.now(CHINA_TZ)
        
        summary_parts = [f"郑总，今日（{now.month}月{now.day}日）工作总结：\n"]
        
        agent_names = {
            "coordinator": "小调", "video_creator": "小影",
            "copywriter": "小文", "sales": "小销",
            "follow": "小跟", "analyst": "小析",
            "lead_hunter": "小猎", "analyst2": "小析2",
            "eu_customs_monitor": "小欧间谍",
        }
        
        async with AsyncSessionLocal() as db:
            # ===== 1. 今日AI任务统计 =====
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'completed') as completed,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending
                    FROM ai_tasks 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
            )
            row = result.fetchone()
            completed, failed, pending = row[0] or 0, row[1] or 0, row[2] or 0
            
            summary_parts.append(f"📊 AI团队任务：完成 {completed} | 失败 {failed} | 待处理 {pending}")
            
            # ===== 2. 各员工工作量 =====
            result = await db.execute(
                text("""
                    SELECT agent_type, COUNT(*) as cnt
                    FROM ai_tasks 
                    WHERE DATE(created_at) = CURRENT_DATE
                    AND status = 'completed'
                    GROUP BY agent_type
                    ORDER BY cnt DESC
                    LIMIT 5
                """)
            )
            top_workers = result.fetchall()
            
            if top_workers:
                summary_parts.append("\n今日最活跃员工：")
                for row in top_workers:
                    name = agent_names.get(row[0], row[0])
                    summary_parts.append(f"  • {name}: {row[1]}个任务")
            
            # ===== 3. 今日日程完成情况 =====
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE is_completed = TRUE) as done,
                        COUNT(*) as total
                    FROM assistant_schedules
                    WHERE DATE(start_time) = CURRENT_DATE
                """)
            )
            row = result.fetchone()
            done_schedules, total_schedules = row[0] or 0, row[1] or 0
            
            if total_schedules > 0:
                summary_parts.append(f"\n📅 今日日程：{done_schedules}/{total_schedules} 完成")
            
            # ===== 4. 明日安排预览 =====
            tomorrow = (now + timedelta(days=1)).date()
            result = await db.execute(
                text("""
                    SELECT title, start_time
                    FROM assistant_schedules
                    WHERE DATE(start_time) = :tomorrow
                    AND is_completed = FALSE
                    ORDER BY start_time ASC
                    LIMIT 5
                """),
                {"tomorrow": tomorrow}
            )
            tomorrow_schedules = result.fetchall()
            
            if tomorrow_schedules:
                weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                weekday = weekday_names[tomorrow.weekday()]
                summary_parts.append(f"\n📌 明日安排（{tomorrow.month}月{tomorrow.day}日 {weekday}）：")
                for s in tomorrow_schedules:
                    if s[1]:
                        if s[1].tzinfo is None:
                            st = pytz.UTC.localize(s[1])
                        else:
                            st = s[1]
                        time_str = st.astimezone(CHINA_TZ).strftime("%H:%M")
                    else:
                        time_str = "全天"
                    summary_parts.append(f"  • {time_str} {s[0]}")
        
        # ===== 5. 邮件情况 =====
        try:
            from app.services.multi_email_service import multi_email_service
            email_summary = await multi_email_service.get_unread_summary()
            unread = email_summary.get("total_unread", 0)
            if unread > 0:
                summary_parts.append(f"\n📬 未读邮件：{unread}封")
        except Exception:
            pass
        
        summary_parts.append("\n辛苦了！有事随时叫我。")
        
        # 发送晚报
        summary = "\n".join(summary_parts)
        await send_text_message("Frank.Z", summary)
        logger.info("[Maria晚报] 晚间工作总结已发送")
        
    except Exception as e:
        logger.error(f"[Maria晚报] 晚间总结生成失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


# ============================================================
# 混合方案新增：自动化工作流任务
# ============================================================

async def maria_auto_process_new_leads():
    """
    Maria 自动处理新线索（每30分钟执行）
    
    工作流：
    1. 查询最近30分钟新发现的线索
    2. 自动分析每条线索的意向等级
    3. 高意向线索：立即通知老板 + 生成跟进建议
    4. 中意向线索：记录待跟进列表
    5. 低意向线索：归档观察
    """
    import fcntl
    lock_file = "/tmp/maria_auto_leads.lock"
    
    try:
        # 文件锁防止重复执行
        with open(lock_file, "w") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                logger.debug("[Maria自动化] 线索处理任务正在执行，跳过")
                return
            
            from app.models.database import AsyncSessionLocal
            from sqlalchemy import text
            from app.api.wechat_assistant import send_text_message
            
            logger.info("[Maria自动化] 开始自动处理新线索...")
            
            async with AsyncSessionLocal() as db:
                # 1. 查询最近30分钟且未处理的新线索
                result = await db.execute(
                    text("""
                        SELECT id, source, source_url, content, ai_summary, intent_level,
                               ai_confidence, language, created_at
                        FROM leads
                        WHERE status = 'new'
                        AND created_at > NOW() - INTERVAL '30 minutes'
                        AND intent_level IS NOT NULL
                        ORDER BY ai_confidence DESC
                        LIMIT 10
                    """)
                )
                new_leads = result.fetchall()
                
                if not new_leads:
                    logger.info("[Maria自动化] 最近30分钟没有新线索")
                    fcntl.flock(f, fcntl.LOCK_UN)
                    return
                
                logger.info(f"[Maria自动化] 发现 {len(new_leads)} 条新线索，开始处理")
                
                high_intent_leads = []
                medium_intent_leads = []
                
                for lead in new_leads:
                    lead_id = lead[0]
                    source = lead[1]
                    source_url = lead[2]
                    content = lead[3]
                    ai_summary = lead[4]
                    intent_level = lead[5]
                    confidence = lead[6]
                    language = lead[7]
                    created_at = lead[8]
                    
                    # 根据意向等级分类
                    if intent_level == 'high':
                        high_intent_leads.append({
                            "id": lead_id,
                            "source": source,
                            "summary": ai_summary or "暂无摘要",
                            "confidence": f"{int(confidence * 100)}%" if confidence else "未知",
                            "url": source_url,
                            "language": language or "zh"
                        })
                        
                        # 更新状态为待跟进
                        await db.execute(
                            text("UPDATE leads SET status = 'following' WHERE id = :id"),
                            {"id": lead_id}
                        )
                        
                    elif intent_level == 'medium':
                        medium_intent_leads.append({
                            "id": lead_id,
                            "source": source,
                            "summary": ai_summary or "暂无摘要"
                        })
                        
                        # 更新状态为已分析
                        await db.execute(
                            text("UPDATE leads SET status = 'analyzed' WHERE id = :id"),
                            {"id": lead_id}
                        )
                    else:
                        # 低意向归档
                        await db.execute(
                            text("UPDATE leads SET status = 'archived' WHERE id = :id"),
                            {"id": lead_id}
                        )
                
                await db.commit()
                
                # 2. 高意向线索立即通知老板
                if high_intent_leads:
                    message = f"🎯 Maria发现 {len(high_intent_leads)} 条高意向线索！\n\n"
                    
                    for i, lead in enumerate(high_intent_leads[:5], 1):
                        message += f"{i}. 【{lead['source']}】\n"
                        message += f"   📝 {lead['summary'][:50]}...\n"
                        message += f"   🎯 意向度: {lead['confidence']}\n"
                        if lead.get('url'):
                            message += f"   🔗 {lead['url'][:50]}...\n"
                        message += "\n"
                    
                    if len(high_intent_leads) > 5:
                        message += f"还有 {len(high_intent_leads) - 5} 条高意向线索...\n"
                    
                    message += "需要我帮您生成跟进话术吗？"
                    
                    await send_text_message("Frank.Z", message)
                    logger.info(f"[Maria自动化] 已通知老板 {len(high_intent_leads)} 条高意向线索")
                
                # 3. 中意向线索汇总（每日汇报，不即时通知）
                if medium_intent_leads:
                    # 记录到日志，晚报时汇总
                    logger.info(f"[Maria自动化] 发现 {len(medium_intent_leads)} 条中意向线索，已记录")
            
            fcntl.flock(f, fcntl.LOCK_UN)
            logger.info("[Maria自动化] 新线索处理完成")
            
    except Exception as e:
        logger.error(f"[Maria自动化] 处理新线索失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def maria_auto_followup_reminder():
    """
    Maria 自动跟进提醒（每天10:00和15:00执行）
    
    功能：
    1. 查询需要今日跟进的客户
    2. 生成跟进话术建议
    3. 发送提醒给老板
    """
    try:
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        from app.api.wechat_assistant import send_text_message
        import pytz
        
        logger.info("[Maria自动化] 检查今日待跟进客户...")
        
        CHINA_TZ = pytz.timezone('Asia/Shanghai')
        now = datetime.now(CHINA_TZ)
        
        async with AsyncSessionLocal() as db:
            # 查询今日需要跟进的客户
            result = await db.execute(
                text("""
                    SELECT c.id, c.name, c.company, c.email, c.intent_level,
                           c.last_contact_at, c.next_contact_at, c.notes
                    FROM customers c
                    WHERE DATE(c.next_contact_at) = CURRENT_DATE
                    AND c.status = 'active'
                    ORDER BY c.intent_level DESC, c.next_contact_at ASC
                    LIMIT 10
                """)
            )
            customers = result.fetchall()
            
            if not customers:
                logger.info("[Maria自动化] 今日没有需要跟进的客户")
                return
            
            # 按意向分组
            high_intent = [c for c in customers if c[4] == 'high']
            other_intent = [c for c in customers if c[4] != 'high']
            
            message = f"📋 郑总，今日有 {len(customers)} 位客户需要跟进：\n\n"
            
            if high_intent:
                message += "🔥 高意向客户（优先）：\n"
                for c in high_intent[:3]:
                    name = c[1] or "未知"
                    company = c[2] or ""
                    email = c[3] or ""
                    last_contact = c[5]
                    notes = c[7] or ""
                    
                    message += f"• {name}"
                    if company:
                        message += f" ({company})"
                    message += "\n"
                    
                    if last_contact:
                        days_ago = (now.date() - last_contact.date()).days
                        message += f"  上次联系: {days_ago}天前\n"
                    
                    if notes:
                        message += f"  备注: {notes[:30]}...\n"
                    
                    message += "\n"
            
            if other_intent:
                message += f"\n📌 其他客户：{len(other_intent)} 位\n"
                for c in other_intent[:3]:
                    name = c[1] or "未知"
                    company = c[2] or ""
                    message += f"• {name}"
                    if company:
                        message += f" ({company})"
                    message += "\n"
            
            message += "\n需要我帮您生成跟进邮件或话术吗？"
            
            await send_text_message("Frank.Z", message)
            logger.info(f"[Maria自动化] 已发送跟进提醒，{len(customers)} 位客户")
            
    except Exception as e:
        logger.error(f"[Maria自动化] 跟进提醒失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def maria_lead_hunt_scheduler():
    """
    Maria 自动线索狩猎调度（每3小时执行）
    
    功能：
    1. 根据时间段智能调度线索搜索
    2. 工作时间(9-21点)执行搜索
    3. 自动调用小猎搜索线索
    4. 搜索完成后触发自动处理流程
    """
    import fcntl
    lock_file = "/tmp/maria_lead_hunt.lock"
    
    try:
        # 检查是否在工作时间
        import pytz
        CHINA_TZ = pytz.timezone('Asia/Shanghai')
        now = datetime.now(CHINA_TZ)
        
        if not (9 <= now.hour < 21):
            logger.info(f"[Maria自动化] 当前 {now.hour}:00 不在工作时间(9-21点)，跳过线索搜索")
            return
        
        # 文件锁防止重复执行
        with open(lock_file, "w") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                logger.debug("[Maria自动化] 线索狩猎任务正在执行，跳过")
                return
            
            logger.info("[Maria自动化] 启动自动线索狩猎...")
            
            # 直接调用小猎的智能狩猎
            from app.agents.lead_hunter import lead_hunter_agent
            
            result = await lead_hunter_agent.process({
                "action": "smart_hunt",
                "max_keywords": 3,  # 每次搜索3个关键词
                "max_results": 15   # 每次最多分析15条
            })
            
            leads_found = result.get("total_leads", 0)
            high_intent = result.get("high_intent_leads", 0)
            
            logger.info(f"[Maria自动化] 线索狩猎完成: 发现 {leads_found} 条线索，高意向 {high_intent} 条")
            
            # 如果发现线索，触发自动处理
            if leads_found > 0:
                await maria_auto_process_new_leads()
            
            fcntl.flock(f, fcntl.LOCK_UN)
            
    except Exception as e:
        logger.error(f"[Maria自动化] 线索狩猎调度失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


# ============================================================
# 小知 - 智能知识采集与迭代任务
# ============================================================

async def xiaozhi_auto_knowledge_collection():
    """
    小知 - 自动知识采集任务（每2小时执行）
    
    功能：
    1. 从群消息中提取有价值的知识
    2. 从客户对话中提取FAQ和痛点
    3. 从海关预警中提取政策知识
    4. 去重、分类、入库
    """
    import fcntl
    lock_file = "/tmp/xiaozhi_knowledge.lock"
    
    try:
        # 文件锁防止重复执行
        with open(lock_file, "w") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                logger.debug("[小知] 知识采集任务正在执行，跳过")
                return
            
            logger.info("[小知] 🧠 启动自动知识采集...")
            
            from app.models.database import async_session_maker
            from sqlalchemy import text
            from app.services.knowledge_base import knowledge_base
            import json
            
            stats = {
                "collected": 0,
                "added": 0,
                "merged": 0,
                "rejected": 0
            }
            
            async with async_session_maker() as db:
                # 1. 从群消息中提取知识（最近2小时的有价值消息）
                try:
                    result = await db.execute(
                        text("""
                            SELECT id, content, analysis_result, group_name
                            FROM wechat_group_messages
                            WHERE created_at > NOW() - INTERVAL '2 hours'
                            AND analysis_result IS NOT NULL
                            AND (analysis_result->>'category' IN ('intel', 'knowledge'))
                            AND NOT EXISTS (
                                SELECT 1 FROM knowledge_base kb 
                                WHERE kb.source_id = CAST(wechat_group_messages.id AS TEXT)
                            )
                            LIMIT 20
                        """)
                    )
                    group_messages = result.fetchall()
                    
                    for msg in group_messages:
                        stats["collected"] += 1
                        msg_id, content, analysis, group_name = msg
                        
                        if analysis:
                            analysis_data = analysis if isinstance(analysis, dict) else json.loads(analysis)
                            category = analysis_data.get("category", "intel")
                            summary = analysis_data.get("summary", content[:200])
                            
                            # 映射到知识类型
                            type_mapping = {
                                "intel": "market_intel",
                                "knowledge": "clearance_exp"
                            }
                            knowledge_type = type_mapping.get(category, "faq")
                            
                            # 提取标签
                            tags = []
                            if "运价" in content or "价格" in content:
                                tags.append("运价")
                                knowledge_type = "price_ref"
                            if "清关" in content or "海关" in content:
                                tags.append("清关")
                            if "政策" in content or "法规" in content:
                                tags.append("政策")
                                knowledge_type = "policy"
                            
                            tags.append(group_name[:20] if group_name else "微信群")
                            
                            # 添加到知识库
                            knowledge_id = await knowledge_base.add_knowledge(
                                content=summary if len(summary) > 50 else content[:500],
                                knowledge_type=knowledge_type,
                                source="wechat_group",
                                source_id=str(msg_id),
                                tags=tags,
                                is_verified=False
                            )
                            
                            if knowledge_id:
                                stats["added"] += 1
                                logger.debug(f"[小知] 从群消息提取知识: {summary[:50]}...")
                            
                except Exception as e:
                    logger.warning(f"[小知] 群消息知识提取失败: {e}")
                
                # 2. 从客户对话中提取FAQ（识别高频问题）
                try:
                    result = await db.execute(
                        text("""
                            SELECT content, COUNT(*) as freq
                            FROM (
                                SELECT LOWER(SUBSTRING(content FROM 1 FOR 50)) as content
                                FROM customer_conversations
                                WHERE created_at > NOW() - INTERVAL '24 hours'
                                AND role = 'user'
                                AND content LIKE '%？%' OR content LIKE '%吗%' OR content LIKE '%怎么%'
                            ) sub
                            GROUP BY content
                            HAVING COUNT(*) >= 2
                            ORDER BY freq DESC
                            LIMIT 5
                        """)
                    )
                    frequent_questions = result.fetchall()
                    
                    for q in frequent_questions:
                        question, freq = q
                        stats["collected"] += 1
                        
                        # 检查是否已有类似FAQ
                        existing = await knowledge_base.search_knowledge(
                            query=question,
                            knowledge_type="faq",
                            limit=1
                        )
                        
                        if not existing:
                            # 标记为需要补充FAQ（暂不自动生成答案）
                            await knowledge_base.add_knowledge(
                                content=f"[待补充答案] 高频问题({freq}次): {question}",
                                knowledge_type="faq",
                                source="customer_chat",
                                tags=["待补充", "高频问题"],
                                is_verified=False
                            )
                            stats["added"] += 1
                            logger.info(f"[小知] 发现高频问题待补充: {question}")
                        else:
                            stats["merged"] += 1
                            
                except Exception as e:
                    logger.warning(f"[小知] 客户对话FAQ提取失败: {e}")
                
                # 3. 从海关预警中提取政策知识
                try:
                    result = await db.execute(
                        text("""
                            SELECT id, title_cn, summary_cn, news_type, urgency
                            FROM customs_alerts
                            WHERE created_at > NOW() - INTERVAL '24 hours'
                            AND importance_score >= 60
                            AND NOT EXISTS (
                                SELECT 1 FROM knowledge_base kb 
                                WHERE kb.source_id = CAST(customs_alerts.id AS TEXT)
                                AND kb.source = 'customs_alert'
                            )
                            LIMIT 10
                        """)
                    )
                    alerts = result.fetchall()
                    
                    for alert in alerts:
                        stats["collected"] += 1
                        alert_id, title, summary, news_type, urgency = alert
                        
                        tags = ["海关", "政策"]
                        if urgency == "紧急":
                            tags.append("紧急")
                        if news_type:
                            tags.append(news_type)
                        
                        knowledge_id = await knowledge_base.add_knowledge(
                            content=f"{title}\n\n{summary}" if summary else title,
                            knowledge_type="policy",
                            source="customs_alert",
                            source_id=str(alert_id),
                            tags=tags,
                            is_verified=True  # 海关预警视为已验证
                        )
                        
                        if knowledge_id:
                            stats["added"] += 1
                            logger.debug(f"[小知] 从海关预警提取知识: {title[:50]}...")
                            
                except Exception as e:
                    logger.warning(f"[小知] 海关预警知识提取失败: {e}")
            
            logger.info(f"[小知] ✅ 知识采集完成: 采集 {stats['collected']} 条，新增 {stats['added']} 条，合并 {stats['merged']} 条，拒绝 {stats['rejected']} 条")
            
            fcntl.flock(f, fcntl.LOCK_UN)
            
    except Exception as e:
        logger.error(f"[小知] 知识采集失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def xiaozhi_knowledge_maintenance():
    """
    小知 - 知识库维护任务（每天凌晨执行）
    
    功能：
    1. 检查过期知识并标记
    2. 统计知识使用情况
    3. 生成知识健康度报告
    4. 清理低质量/无用知识
    """
    try:
        logger.info("[小知] 🔧 启动知识库维护...")
        
        from app.models.database import async_session_maker
        from sqlalchemy import text
        
        async with async_session_maker() as db:
            # 1. 标记过期知识（运价参考超过7天）
            result = await db.execute(
                text("""
                    UPDATE knowledge_base
                    SET tags = array_append(tags, '过期待更新')
                    WHERE knowledge_type = 'price_ref'
                    AND updated_at < NOW() - INTERVAL '7 days'
                    AND NOT ('过期待更新' = ANY(tags))
                    RETURNING id
                """)
            )
            expired_price = len(result.fetchall())
            
            # 2. 标记过期政策（超过30天）
            result = await db.execute(
                text("""
                    UPDATE knowledge_base
                    SET tags = array_append(tags, '待复核')
                    WHERE knowledge_type = 'policy'
                    AND updated_at < NOW() - INTERVAL '30 days'
                    AND NOT ('待复核' = ANY(tags))
                    RETURNING id
                """)
            )
            expired_policy = len(result.fetchall())
            
            # 3. 清理从未使用且超过90天的未验证知识
            result = await db.execute(
                text("""
                    DELETE FROM knowledge_base
                    WHERE usage_count = 0
                    AND is_verified = FALSE
                    AND created_at < NOW() - INTERVAL '90 days'
                    RETURNING id
                """)
            )
            cleaned = len(result.fetchall())
            
            # 4. 统计知识库健康度
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE is_verified = TRUE) as verified,
                        COUNT(*) FILTER (WHERE usage_count > 0) as used,
                        COUNT(*) FILTER (WHERE '过期待更新' = ANY(tags) OR '待复核' = ANY(tags)) as needs_attention
                    FROM knowledge_base
                """)
            )
            stats = result.fetchone()
            
            await db.commit()
            
            total, verified, used, needs_attention = stats if stats else (0, 0, 0, 0)
            health_score = int((verified / max(total, 1) * 40) + (used / max(total, 1) * 40) + ((1 - needs_attention / max(total, 1)) * 20))
            
            logger.info(f"[小知] ✅ 知识库维护完成:")
            logger.info(f"  - 运价过期标记: {expired_price} 条")
            logger.info(f"  - 政策待复核: {expired_policy} 条")
            logger.info(f"  - 清理无用知识: {cleaned} 条")
            logger.info(f"  - 知识库总量: {total} 条")
            logger.info(f"  - 已验证: {verified} 条")
            logger.info(f"  - 使用过: {used} 条")
            logger.info(f"  - 健康度评分: {health_score}/100")
            
    except Exception as e:
        logger.error(f"[小知] 知识库维护失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def xiaozhi_knowledge_gap_check():
    """
    小知 - 知识缺口检查（每周执行）
    
    功能：
    1. 分析客户高频问题 vs 知识库覆盖
    2. 识别知识缺口
    3. 生成补充建议
    """
    try:
        logger.info("[小知] 🔍 启动知识缺口分析...")
        
        from app.models.database import async_session_maker
        from sqlalchemy import text
        
        gaps = []
        
        async with async_session_maker() as db:
            # 1. 分析最近一周的客户高频问题
            result = await db.execute(
                text("""
                    SELECT 
                        CASE 
                            WHEN content ILIKE '%时效%' OR content ILIKE '%多久%' THEN '时效查询'
                            WHEN content ILIKE '%价格%' OR content ILIKE '%多少钱%' OR content ILIKE '%报价%' THEN '价格咨询'
                            WHEN content ILIKE '%清关%' OR content ILIKE '%海关%' THEN '清关问题'
                            WHEN content ILIKE '%VAT%' OR content ILIKE '%税%' THEN 'VAT税务'
                            WHEN content ILIKE '%带电%' OR content ILIKE '%电池%' THEN '带电产品'
                            WHEN content ILIKE '%退货%' OR content ILIKE '%退回%' THEN '退货处理'
                            ELSE '其他'
                        END as topic,
                        COUNT(*) as freq
                    FROM customer_conversations
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    AND role = 'user'
                    GROUP BY topic
                    HAVING COUNT(*) >= 3
                    ORDER BY freq DESC
                """)
            )
            hot_topics = result.fetchall()
            
            # 2. 检查每个热门话题的知识覆盖
            for topic, freq in hot_topics:
                if topic == '其他':
                    continue
                    
                # 搜索相关知识
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM knowledge_base
                        WHERE content ILIKE :pattern
                        AND is_verified = TRUE
                    """),
                    {"pattern": f"%{topic.replace('查询', '').replace('咨询', '').replace('问题', '')}%"}
                )
                coverage = result.scalar() or 0
                
                if coverage < 3:  # 相关知识少于3条视为缺口
                    gaps.append({
                        "topic": topic,
                        "query_frequency": freq,
                        "knowledge_coverage": coverage,
                        "severity": "高" if coverage == 0 else "中"
                    })
            
            if gaps:
                logger.warning(f"[小知] ⚠️ 发现 {len(gaps)} 个知识缺口:")
                for gap in gaps:
                    logger.warning(f"  - {gap['topic']}: 咨询{gap['query_frequency']}次，知识覆盖{gap['knowledge_coverage']}条")
                
                # 可以在这里发送通知给老板
                # TODO: 集成通知功能
            else:
                logger.info("[小知] ✅ 知识覆盖良好，未发现明显缺口")
                
    except Exception as e:
        logger.error(f"[小知] 知识缺口分析失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
