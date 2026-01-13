"""
对话服务 - 保存对话记录到数据库
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.database import async_session_maker


class ConversationService:
    """对话服务"""
    
    async def record_agent_task(
        self,
        agent_type: str,
        success: bool = True
    ) -> bool:
        """记录AI员工完成任务"""
        async with async_session_maker() as db:
            try:
                # 更新今日任务数和总任务数
                await db.execute(
                    text("""
                        UPDATE ai_agents 
                        SET tasks_completed_today = tasks_completed_today + 1,
                            total_tasks_completed = total_tasks_completed + 1,
                            updated_at = NOW()
                        WHERE agent_type = :agent_type
                    """),
                    {"agent_type": agent_type}
                )
                await db.commit()
                logger.info(f"✅ 记录 {agent_type} 员工任务完成")
                return True
            except Exception as e:
                logger.error(f"记录AI员工任务失败: {e}")
                await db.rollback()
                return False
    """对话服务"""
    
    async def get_or_create_customer(
        self,
        wechat_id: str,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取或创建客户记录"""
        async with async_session_maker() as db:
            try:
                # 查找现有客户
                result = await db.execute(
                    text("SELECT id, name, intent_score FROM customers WHERE wechat_id = :wechat_id"),
                    {"wechat_id": wechat_id}
                )
                row = result.fetchone()
                
                if row:
                    return {
                        "id": str(row[0]),
                        "name": row[1],
                        "intent_score": row[2],
                        "is_new": False
                    }
                
                # 创建新客户
                customer_name = name or f"微信用户_{wechat_id[:8]}"
                result = await db.execute(
                    text("""
                        INSERT INTO customers (wechat_id, name, source, intent_score, created_at, updated_at)
                        VALUES (:wechat_id, :name, 'wechat', 0, NOW(), NOW())
                        RETURNING id
                    """),
                    {"wechat_id": wechat_id, "name": customer_name}
                )
                customer_id = result.fetchone()[0]
                await db.commit()
                
                logger.info(f"✅ 创建新客户: {customer_name} (ID: {customer_id})")
                
                return {
                    "id": str(customer_id),
                    "name": customer_name,
                    "intent_score": 0,
                    "is_new": True
                }
                
            except Exception as e:
                logger.error(f"获取/创建客户失败: {e}")
                await db.rollback()
                return {"id": None, "name": None, "is_new": False}
    
    async def save_message(
        self,
        customer_id: str,
        agent_type: str,
        message_type: str,  # 'inbound' or 'outbound'
        content: str,
        intent_delta: int = 0
    ) -> bool:
        """保存对话消息"""
        async with async_session_maker() as db:
            try:
                await db.execute(
                    text("""
                        INSERT INTO conversations 
                        (customer_id, agent_type, message_type, content, intent_delta, created_at)
                        VALUES (:customer_id, :agent_type, :message_type, :content, :intent_delta, NOW())
                    """),
                    {
                        "customer_id": customer_id,
                        "agent_type": agent_type,
                        "message_type": message_type,
                        "content": content,
                        "intent_delta": intent_delta
                    }
                )
                await db.commit()
                
                logger.info(f"✅ 保存消息: [{agent_type}] {message_type} - {content[:30]}...")
                return True
                
            except Exception as e:
                logger.error(f"保存消息失败: {e}")
                await db.rollback()
                return False
    
    async def update_customer_intent(
        self,
        customer_id: str,
        intent_delta: int
    ) -> bool:
        """更新客户意向分数"""
        async with async_session_maker() as db:
            try:
                await db.execute(
                    text("""
                        UPDATE customers 
                        SET intent_score = GREATEST(0, LEAST(100, intent_score + :delta)),
                            updated_at = NOW()
                        WHERE id = :customer_id
                    """),
                    {"customer_id": customer_id, "delta": intent_delta}
                )
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"更新意向分数失败: {e}")
                await db.rollback()
                return False
    
    async def get_conversation_count(self, today_only: bool = False) -> int:
        """获取对话数量"""
        async with async_session_maker() as db:
            try:
                if today_only:
                    result = await db.execute(
                        text("SELECT COUNT(*) FROM conversations WHERE DATE(created_at) = CURRENT_DATE")
                    )
                else:
                    result = await db.execute(text("SELECT COUNT(*) FROM conversations"))
                return result.scalar() or 0
            except Exception as e:
                logger.error(f"获取对话数量失败: {e}")
                return 0
    
    async def get_customer_count(self, today_only: bool = False) -> int:
        """获取客户数量"""
        async with async_session_maker() as db:
            try:
                if today_only:
                    result = await db.execute(
                        text("SELECT COUNT(*) FROM customers WHERE DATE(created_at) = CURRENT_DATE")
                    )
                else:
                    result = await db.execute(text("SELECT COUNT(*) FROM customers"))
                return result.scalar() or 0
            except Exception as e:
                logger.error(f"获取客户数量失败: {e}")
                return 0


# 创建单例
conversation_service = ConversationService()
