"""
通知服务 - 多渠道通知中心
支持企业微信、邮件、系统内通知三种渠道
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from app.core.config import settings
from app.models.database import async_session_maker


class NotificationService:
    """多渠道通知服务"""
    
    def __init__(self):
        self.wechat_enabled = bool(settings.WECHAT_CORP_ID)
        self.email_enabled = bool(getattr(settings, 'SMTP_HOST', ''))
        # 通知接收者企业微信ID（老板）
        self.notify_wechat_users = getattr(settings, 'NOTIFY_WECHAT_USERS', '').split(',') if getattr(settings, 'NOTIFY_WECHAT_USERS', '') else []
    
    async def notify_high_intent_customer(
        self,
        customer_id: str,
        customer_name: str,
        intent_score: int,
        intent_level: str,
        key_signals: List[str],
        company: Optional[str] = None,
        phone: Optional[str] = None,
        last_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        高意向客户多渠道通知
        
        Args:
            customer_id: 客户ID
            customer_name: 客户名称
            intent_score: 意向分数
            intent_level: 意向等级
            key_signals: 关键信号
            company: 公司名称
            phone: 联系电话
            last_message: 最近消息
        """
        notification = {
            "type": "high_intent",
            "title": f"🔥 发现高意向客户: {customer_name}",
            "content": f"""
意向等级: {intent_level}级
意向分数: {intent_score}分
公司: {company or '未知'}
电话: {phone or '未知'}
关键信号: {', '.join(key_signals) if key_signals else '无'}
最近消息: {last_message[:100] if last_message else '无'}

建议立即跟进！
            """.strip(),
            "customer_id": customer_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        results = {
            "notification": notification,
            "channels": {}
        }
        
        # 1. 系统内通知（保存到数据库）
        system_result = await self._save_system_notification(
            notification_type="high_intent",
            title=notification["title"],
            content=notification["content"],
            customer_id=customer_id
        )
        results["channels"]["system"] = system_result
        
        # 2. 企业微信通知
        if self.wechat_enabled:
            wechat_result = await self._send_wechat_notification(
                title=notification["title"],
                content=self._format_wechat_message(
                    customer_name=customer_name,
                    intent_score=intent_score,
                    intent_level=intent_level,
                    company=company,
                    phone=phone,
                    key_signals=key_signals,
                    last_message=last_message
                )
            )
            results["channels"]["wechat"] = wechat_result
        
        # 3. 邮件通知
        if self.email_enabled:
            try:
                from app.services.email_service import email_service
                email_result = await email_service.notify_high_intent_customer(
                    customer_name=customer_name,
                    company=company,
                    intent_score=intent_score,
                    intent_level=intent_level,
                    key_signals=key_signals,
                    last_message=last_message,
                    customer_phone=phone
                )
                results["channels"]["email"] = email_result
            except Exception as e:
                logger.error(f"邮件通知失败: {e}")
                results["channels"]["email"] = {"status": "error", "message": str(e)}
        
        logger.info(f"📢 高意向客户通知已发送: {customer_name} ({intent_level}级)")
        
        return results
    
    def _format_wechat_message(
        self,
        customer_name: str,
        intent_score: int,
        intent_level: str,
        company: Optional[str],
        phone: Optional[str],
        key_signals: List[str],
        last_message: Optional[str]
    ) -> str:
        """格式化企业微信Markdown消息"""
        signals_text = "\n".join([f"> - {s}" for s in key_signals]) if key_signals else "> 无"
        
        return f"""# 🔥 发现高意向客户

**客户**: {customer_name}
**公司**: {company or '未知'}
**电话**: {phone or '未知'}

---

**意向评分**: <font color="warning">{intent_score}分</font>
**意向等级**: <font color="warning">{intent_level}级</font>

---

**关键信号**:
{signals_text}

---

**最近消息**:
> {last_message[:100] if last_message else '无'}

---

⚡ **建议立即跟进，促成签约！**
"""
    
    async def notify_task_complete(
        self,
        task_type: str,
        task_id: str,
        result_summary: str
    ) -> Dict[str, Any]:
        """通知任务完成"""
        notification = {
            "type": "task_complete",
            "title": f"✅ 任务完成: {task_type}",
            "content": result_summary,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 只保存系统通知
        await self._save_system_notification(
            notification_type="task_complete",
            title=notification["title"],
            content=notification["content"],
            task_id=task_id
        )
        
        return {"notification": notification}
    
    async def notify_daily_summary(
        self,
        new_customers: int,
        high_intent_count: int,
        conversations: int,
        follow_count: int,
        videos_generated: int,
        top_customers: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送每日总结"""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        notification = {
            "type": "daily_summary",
            "title": f"📊 {date_str} 工作总结",
            "content": f"""
今日新增客户: {new_customers}
高意向客户: {high_intent_count}
对话数量: {conversations}
跟进次数: {follow_count}
视频生成: {videos_generated}
            """.strip(),
            "timestamp": datetime.utcnow().isoformat(),
            "action_url": f"/reports/{date_str}"  # 添加跳转链接
        }
        
        results = {
            "notification": notification,
            "channels": {}
        }
        
        # 1. 系统通知（带去重检查）
        system_result = await self._save_system_notification_with_dedup(
            notification_type="daily_summary",
            title=notification["title"],
            content=notification["content"],
            action_url=notification["action_url"],
            dedup_key=f"daily_summary_{date_str}"  # 按日期去重
        )
        results["channels"]["system"] = system_result
        
        # 2. 邮件通知
        if self.email_enabled:
            try:
                from app.services.email_service import email_service
                email_result = await email_service.send_daily_summary(
                    date=date_str,
                    new_customers=new_customers,
                    high_intent_count=high_intent_count,
                    conversations=conversations,
                    follow_count=follow_count,
                    videos_generated=videos_generated,
                    top_customers=top_customers
                )
                results["channels"]["email"] = email_result
            except Exception as e:
                logger.error(f"每日汇总邮件发送失败: {e}")
                results["channels"]["email"] = {"status": "error", "message": str(e)}
        
        return results
    
    async def notify_follow_reminder(
        self,
        customers_to_follow: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """发送跟进提醒"""
        if not customers_to_follow:
            return {"status": "skipped", "message": "无待跟进客户"}
        
        count = len(customers_to_follow)
        notification = {
            "type": "follow_reminder",
            "title": f"📞 今日有 {count} 位客户需要跟进",
            "content": "\n".join([
                f"- {c.get('name', '未知')} ({c.get('intent_level', 'C')}级)"
                for c in customers_to_follow[:10]
            ]),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        results = {"notification": notification, "channels": {}}
        
        # 系统通知
        await self._save_system_notification(
            notification_type="follow_reminder",
            title=notification["title"],
            content=notification["content"]
        )
        results["channels"]["system"] = {"status": "saved"}
        
        # 企业微信通知
        if self.wechat_enabled:
            wechat_content = f"""# 📞 跟进提醒

今日有 **{count}** 位客户需要跟进:

""" + "\n".join([
                f"- {c.get('name', '未知')} ({c.get('intent_level', 'C')}级) - {c.get('company', '')}"
                for c in customers_to_follow[:10]
            ])
            
            if count > 10:
                wechat_content += f"\n\n... 还有 {count - 10} 位客户"
            
            results["channels"]["wechat"] = await self._send_wechat_notification(
                title="跟进提醒",
                content=wechat_content
            )
        
        return results
    
    async def _save_system_notification(
        self, 
        notification_type: str,
        title: str,
        content: str,
        customer_id: Optional[str] = None,
        task_id: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> Dict[str, str]:
        """保存系统通知到数据库"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO notifications (type, title, content, customer_id, task_id, action_url, created_at)
                        VALUES (:type, :title, :content, :customer_id, :task_id, :action_url, NOW())
                    """),
                    {
                        "type": notification_type,
                        "title": title,
                        "content": content,
                        "customer_id": customer_id,
                        "task_id": task_id,
                        "action_url": action_url
                    }
                )
                await db.commit()
                return {"status": "saved"}
        except Exception as e:
            logger.error(f"保存系统通知失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _save_system_notification_with_dedup(
        self, 
        notification_type: str,
        title: str,
        content: str,
        dedup_key: str,
        customer_id: Optional[str] = None,
        task_id: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> Dict[str, str]:
        """
        保存系统通知到数据库（带去重）
        如果当天已存在相同 dedup_key 的通知，则跳过
        """
        try:
            async with async_session_maker() as db:
                # 检查今天是否已存在相同的通知
                result = await db.execute(
                    text("""
                        SELECT id FROM notifications 
                        WHERE type = :type 
                        AND title = :title
                        AND DATE(created_at) = CURRENT_DATE
                        LIMIT 1
                    """),
                    {
                        "type": notification_type,
                        "title": title
                    }
                )
                existing = result.fetchone()
                
                if existing:
                    logger.info(f"通知已存在，跳过重复: {title}")
                    return {"status": "skipped", "message": "通知已存在"}
                
                # 不存在则创建
                await db.execute(
                    text("""
                        INSERT INTO notifications (type, title, content, customer_id, task_id, action_url, created_at)
                        VALUES (:type, :title, :content, :customer_id, :task_id, :action_url, NOW())
                    """),
                    {
                        "type": notification_type,
                        "title": title,
                        "content": content,
                        "customer_id": customer_id,
                        "task_id": task_id,
                        "action_url": action_url
                    }
                )
                await db.commit()
                return {"status": "saved"}
        except Exception as e:
            logger.error(f"保存系统通知失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _send_wechat_notification(
        self, 
        title: str,
        content: str
    ) -> Dict[str, str]:
        """发送企业微信通知"""
        if not self.wechat_enabled:
            return {"status": "disabled", "message": "企业微信未配置"}
        
        if not self.notify_wechat_users:
            return {"status": "skipped", "message": "未配置通知接收人"}
        
        try:
            from app.services.wechat import wechat_service
            
            # 发送Markdown消息
            result = await wechat_service.send_markdown_message(
                user_ids=self.notify_wechat_users,
                content=content
            )
            
            if result.get("errcode") == 0:
                logger.info(f"企业微信通知发送成功: {title}")
                return {"status": "sent"}
            else:
                logger.error(f"企业微信通知发送失败: {result}")
                return {"status": "error", "message": str(result)}
                
        except Exception as e:
            logger.error(f"企业微信通知发送异常: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_unread_notifications(
        self,
        user_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取未读通知"""
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        SELECT id, type, title, content, customer_id, task_id, created_at
                        FROM notifications
                        WHERE is_read = false
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "type": row[1],
                        "title": row[2],
                        "content": row[3],
                        "customer_id": str(row[4]) if row[4] else None,
                        "task_id": str(row[5]) if row[5] else None,
                        "created_at": row[6].isoformat() if row[6] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取未读通知失败: {e}")
            return []
    
    async def mark_notification_read(
        self,
        notification_id: str
    ) -> bool:
        """标记通知为已读"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE notifications 
                        SET is_read = true, read_at = NOW()
                        WHERE id = :notification_id
                    """),
                    {"notification_id": notification_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"标记通知已读失败: {e}")
            return False
    
    async def mark_all_read(self) -> int:
        """标记所有通知为已读"""
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        UPDATE notifications 
                        SET is_read = true, read_at = NOW()
                        WHERE is_read = false
                    """)
                )
                await db.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"标记所有通知已读失败: {e}")
            return 0
    
    async def create_notification(
        self,
        title: str,
        content: str,
        notification_type: str = "system",
        priority: str = "medium",
        related_id: Optional[str] = None,
        related_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建系统通知
        
        Args:
            title: 通知标题
            content: 通知内容
            notification_type: 通知类型
            priority: 优先级 (high/medium/low)
            related_id: 关联ID (客户ID、任务ID等)
            related_type: 关联类型 (customer/task/lead等)
        """
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO notifications (type, title, content, customer_id, priority, created_at)
                        VALUES (:type, :title, :content, :customer_id, :priority, NOW())
                    """),
                    {
                        "type": notification_type,
                        "title": title,
                        "content": content,
                        "customer_id": related_id if related_type == "customer" else None,
                        "priority": priority
                    }
                )
                await db.commit()
                logger.info(f"📢 通知已创建: {title}")
                return {"status": "saved", "title": title}
        except Exception as e:
            logger.error(f"创建通知失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def send_to_boss(
        self,
        title: str,
        content: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        发送消息给老板
        
        Args:
            title: 消息标题
            content: 消息内容
            priority: 优先级 (urgent/high/normal/low)
        """
        results = {"channels": {}}
        
        # 1. 保存系统通知
        await self._save_system_notification(
            notification_type="boss_message",
            title=title,
            content=content
        )
        results["channels"]["system"] = {"status": "saved"}
        
        # 2. 企业微信通知
        if self.wechat_enabled:
            # 紧急消息添加特殊标记
            prefix = ""
            if priority == "urgent":
                prefix = "⚠️ 【紧急】"
            elif priority == "high":
                prefix = "🔔 【重要】"
            
            wechat_content = f"""# {prefix}{title}

{content}
"""
            results["channels"]["wechat"] = await self._send_wechat_notification(
                title=title,
                content=wechat_content
            )
        
        # 3. 邮件通知（重要消息）
        if self.email_enabled and priority in ["urgent", "high"]:
            try:
                from app.services.email_service import email_service
                email_result = await email_service.send_simple_notification(
                    subject=title,
                    content=content
                )
                results["channels"]["email"] = email_result
            except Exception as e:
                logger.error(f"邮件通知发送失败: {e}")
                results["channels"]["email"] = {"status": "error", "message": str(e)}
        
        logger.info(f"📢 老板通知已发送: {title}")
        
        return results


# 创建单例
notification_service = NotificationService()
