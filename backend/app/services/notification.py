"""
通知服务
负责高意向客户推送等通知功能
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from loguru import logger

from app.core.config import settings


class NotificationService:
    """通知服务"""
    
    def __init__(self):
        self.wechat_enabled = bool(settings.WECHAT_CORP_ID)
    
    async def notify_high_intent_customer(
        self,
        customer_id: str,
        customer_name: str,
        intent_score: int,
        intent_level: str,
        key_signals: List[str]
    ) -> Dict[str, Any]:
        """
        通知高意向客户
        
        Args:
            customer_id: 客户ID
            customer_name: 客户名称
            intent_score: 意向分数
            intent_level: 意向等级
            key_signals: 关键信号
        """
        notification = {
            "type": "high_intent",
            "title": f"🔥 发现高意向客户: {customer_name}",
            "content": f"""
意向等级: {intent_level}级
意向分数: {intent_score}分
关键信号: {', '.join(key_signals)}

建议立即跟进！
            """.strip(),
            "customer_id": customer_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 发送通知
        results = {
            "notification": notification,
            "channels": {}
        }
        
        # 系统内通知（保存到数据库）
        results["channels"]["system"] = await self._save_system_notification(notification)
        
        # 企业微信通知
        if self.wechat_enabled:
            results["channels"]["wechat"] = await self._send_wechat_notification(notification)
        
        logger.info(f"📢 高意向客户通知已发送: {customer_name} ({intent_level}级)")
        
        return results
    
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
        
        return {"notification": notification}
    
    async def notify_daily_summary(
        self,
        new_customers: int,
        high_intent_count: int,
        conversations: int,
        videos_generated: int
    ) -> Dict[str, Any]:
        """发送每日总结"""
        notification = {
            "type": "daily_summary",
            "title": "📊 今日工作总结",
            "content": f"""
今日新增客户: {new_customers}
高意向客户: {high_intent_count}
对话数量: {conversations}
视频生成: {videos_generated}
            """.strip(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {"notification": notification}
    
    async def _save_system_notification(
        self, 
        notification: Dict[str, Any]
    ) -> Dict[str, str]:
        """保存系统通知到数据库"""
        # TODO: 实际保存到数据库
        return {"status": "saved"}
    
    async def _send_wechat_notification(
        self, 
        notification: Dict[str, Any]
    ) -> Dict[str, str]:
        """发送企业微信通知"""
        if not self.wechat_enabled:
            return {"status": "disabled", "message": "企业微信未配置"}
        
        # TODO: 调用企业微信API发送消息
        # from app.services.wechat import wechat_service
        # return await wechat_service.send_text_message(...)
        
        return {"status": "sent"}


# 创建单例
notification_service = NotificationService()
