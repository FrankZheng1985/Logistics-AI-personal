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


async def check_important_emails_and_notify():
    """
    检查重要邮件并主动通知用户（增强版）
    - VIP发件人（可配置）
    - 包含紧急关键词
    - 大额订单相关
    - 回复/转发的邮件
    - 客户域名邮件
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
                    important_emails.append({
                        "subject": email.get("subject", "(无主题)"),
                        "from": email.get("from_name") or email.get("from_address"),
                        "account": account.get("name"),
                        "reason": reason,
                        "preview": (email.get("body_preview", "") or "")[:60],
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
