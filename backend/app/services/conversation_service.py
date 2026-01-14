"""
对话服务 - 完整的对话处理和记录服务
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.database import async_session_maker


class ConversationService:
    """对话服务 - 提供对话相关的所有数据库操作"""
    
    async def record_agent_task(
        self,
        agent_type: str,
        success: bool = True
    ) -> bool:
        """记录AI员工完成任务"""
        async with async_session_maker() as db:
            try:
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
    
    async def get_or_create_customer(
        self,
        wechat_id: str,
        name: Optional[str] = None,
        channel: str = "wechat"
    ) -> Dict[str, Any]:
        """获取或创建客户记录"""
        async with async_session_maker() as db:
            try:
                # 查找现有客户
                result = await db.execute(
                    text("SELECT id, name, intent_score, intent_level, follow_count FROM customers WHERE wechat_id = :wechat_id"),
                    {"wechat_id": wechat_id}
                )
                row = result.fetchone()
                
                if row:
                    return {
                        "id": str(row[0]),
                        "name": row[1],
                        "intent_score": row[2],
                        "intent_level": row[3],
                        "follow_count": row[4],
                        "is_new": False
                    }
                
                # 创建新客户
                customer_name = name or f"微信用户_{wechat_id[:8]}"
                result = await db.execute(
                    text("""
                        INSERT INTO customers (wechat_id, name, source, intent_score, intent_level, created_at, updated_at)
                        VALUES (:wechat_id, :name, :source, 0, 'C', NOW(), NOW())
                        RETURNING id
                    """),
                    {"wechat_id": wechat_id, "name": customer_name, "source": channel}
                )
                customer_id = result.fetchone()[0]
                await db.commit()
                
                logger.info(f"✅ 创建新客户: {customer_name} (ID: {customer_id})")
                
                return {
                    "id": str(customer_id),
                    "name": customer_name,
                    "intent_score": 0,
                    "intent_level": "C",
                    "follow_count": 0,
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
        intent_delta: int = 0,
        session_id: Optional[str] = None
    ) -> bool:
        """保存对话消息"""
        async with async_session_maker() as db:
            try:
                if not session_id:
                    session_id = f"session_{customer_id}_{datetime.utcnow().strftime('%Y%m%d')}"
                
                await db.execute(
                    text("""
                        INSERT INTO conversations 
                        (customer_id, agent_type, message_type, content, intent_delta, session_id, created_at)
                        VALUES (:customer_id, :agent_type, :message_type, :content, :intent_delta, :session_id, NOW())
                    """),
                    {
                        "customer_id": customer_id,
                        "agent_type": agent_type,
                        "message_type": message_type,
                        "content": content,
                        "intent_delta": intent_delta,
                        "session_id": session_id
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
        intent_delta: int,
        new_score: Optional[int] = None
    ) -> Dict[str, Any]:
        """更新客户意向分数"""
        async with async_session_maker() as db:
            try:
                # 先获取当前分数
                result = await db.execute(
                    text("SELECT intent_score, intent_level FROM customers WHERE id = :customer_id"),
                    {"customer_id": customer_id}
                )
                row = result.fetchone()
                if not row:
                    return {"success": False, "error": "客户不存在"}
                
                old_score = row[0]
                old_level = row[1]
                
                # 计算新分数
                if new_score is not None:
                    final_score = new_score
                else:
                    final_score = max(0, min(100, old_score + intent_delta))
                
                # 计算新等级
                if final_score >= 80:
                    new_level = 'S'
                elif final_score >= 60:
                    new_level = 'A'
                elif final_score >= 30:
                    new_level = 'B'
                else:
                    new_level = 'C'
                
                # 更新数据库
                await db.execute(
                    text("""
                        UPDATE customers 
                        SET intent_score = :score,
                            intent_level = :level,
                            updated_at = NOW()
                        WHERE id = :customer_id
                    """),
                    {"customer_id": customer_id, "score": final_score, "level": new_level}
                )
                await db.commit()
                
                level_changed = old_level != new_level
                upgraded_to_high = new_level in ['S', 'A'] and old_level not in ['S', 'A']
                
                return {
                    "success": True,
                    "old_score": old_score,
                    "new_score": final_score,
                    "old_level": old_level,
                    "new_level": new_level,
                    "level_changed": level_changed,
                    "upgraded_to_high": upgraded_to_high
                }
                
            except Exception as e:
                logger.error(f"更新意向分数失败: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    async def update_customer_contact(
        self,
        customer_id: str
    ) -> bool:
        """更新客户最后联系时间和跟进次数"""
        async with async_session_maker() as db:
            try:
                await db.execute(
                    text("""
                        UPDATE customers 
                        SET last_contact_at = NOW(),
                            follow_count = follow_count + 1,
                            updated_at = NOW()
                        WHERE id = :customer_id
                    """),
                    {"customer_id": customer_id}
                )
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"更新客户联系时间失败: {e}")
                await db.rollback()
                return False
    
    async def get_chat_history(
        self,
        customer_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取客户对话历史"""
        async with async_session_maker() as db:
            try:
                result = await db.execute(
                    text("""
                        SELECT agent_type, message_type, content, created_at
                        FROM conversations
                        WHERE customer_id = :customer_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"customer_id": customer_id, "limit": limit}
                )
                rows = result.fetchall()
                
                return [
                    {
                        "agent_type": row[0],
                        "message_type": row[1],
                        "content": row[2],
                        "created_at": row[3].isoformat() if row[3] else None
                    }
                    for row in reversed(rows)  # 按时间正序返回
                ]
            except Exception as e:
                logger.error(f"获取对话历史失败: {e}")
                return []
    
    async def get_customer_info(
        self,
        customer_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取客户完整信息"""
        async with async_session_maker() as db:
            try:
                result = await db.execute(
                    text("""
                        SELECT id, name, phone, email, wechat_id, company, 
                               source, intent_score, intent_level, 
                               follow_count, last_contact_at, created_at
                        FROM customers
                        WHERE id = :customer_id
                    """),
                    {"customer_id": customer_id}
                )
                row = result.fetchone()
                
                if not row:
                    return None
                
                return {
                    "id": str(row[0]),
                    "name": row[1],
                    "phone": row[2],
                    "email": row[3],
                    "wechat_id": row[4],
                    "company": row[5],
                    "source": row[6],
                    "intent_score": row[7],
                    "intent_level": row[8],
                    "follow_count": row[9],
                    "last_contact_at": row[10].isoformat() if row[10] else None,
                    "created_at": row[11].isoformat() if row[11] else None
                }
            except Exception as e:
                logger.error(f"获取客户信息失败: {e}")
                return None
    
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
    
    async def get_high_intent_count(self, today_only: bool = False) -> int:
        """获取高意向客户数量"""
        async with async_session_maker() as db:
            try:
                if today_only:
                    result = await db.execute(
                        text("""
                            SELECT COUNT(*) FROM customers 
                            WHERE intent_level IN ('S', 'A') 
                            AND DATE(updated_at) = CURRENT_DATE
                        """)
                    )
                else:
                    result = await db.execute(
                        text("SELECT COUNT(*) FROM customers WHERE intent_level IN ('S', 'A')")
                    )
                return result.scalar() or 0
            except Exception as e:
                logger.error(f"获取高意向客户数量失败: {e}")
                return 0
    
    async def get_customers_need_follow(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取需要跟进的客户列表"""
        async with async_session_maker() as db:
            try:
                result = await db.execute(
                    text("""
                        SELECT id, name, company, intent_level, intent_score, 
                               last_contact_at, next_follow_at
                        FROM customers
                        WHERE is_active = true
                        AND (
                            next_follow_at <= NOW()
                            OR (
                                next_follow_at IS NULL 
                                AND last_contact_at IS NOT NULL
                                AND (
                                    (intent_level = 'S' AND last_contact_at < NOW() - INTERVAL '1 day')
                                    OR (intent_level = 'A' AND last_contact_at < NOW() - INTERVAL '2 days')
                                    OR (intent_level = 'B' AND last_contact_at < NOW() - INTERVAL '5 days')
                                    OR (intent_level = 'C' AND last_contact_at < NOW() - INTERVAL '15 days')
                                )
                            )
                        )
                        ORDER BY 
                            CASE intent_level 
                                WHEN 'S' THEN 1 
                                WHEN 'A' THEN 2 
                                WHEN 'B' THEN 3 
                                ELSE 4 
                            END,
                            last_contact_at ASC
                        LIMIT :limit
                    """),
                    {"limit": limit}
                )
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "company": row[2],
                        "intent_level": row[3],
                        "intent_score": row[4],
                        "last_contact_at": row[5].isoformat() if row[5] else None,
                        "next_follow_at": row[6].isoformat() if row[6] else None
                    }
                    for row in rows
                ]
            except Exception as e:
                logger.error(f"获取需跟进客户失败: {e}")
                return []


# 创建单例
conversation_service = ConversationService()
