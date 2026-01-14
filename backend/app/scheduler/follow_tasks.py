"""
跟进相关定时任务
包括：每日跟进检查、未回复检查、每日汇总等
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.services.conversation_service import conversation_service
from app.services.notification import notification_service
from app.agents.follow_agent import follow_agent
from app.core.config import settings


async def daily_follow_check():
    """
    每日跟进检查任务
    检查所有需要跟进的客户，生成跟进提醒
    """
    logger.info("📅 开始执行: 每日跟进检查")
    
    try:
        # 获取需要跟进的客户
        customers = await conversation_service.get_customers_need_follow(limit=100)
        
        if not customers:
            logger.info("📅 没有需要跟进的客户")
            return
        
        logger.info(f"📅 发现 {len(customers)} 位客户需要跟进")
        
        # 按意向等级分组统计
        by_level = {}
        for c in customers:
            level = c.get("intent_level", "C")
            by_level[level] = by_level.get(level, 0) + 1
        
        logger.info(f"📅 按等级分布: {by_level}")
        
        # 发送跟进提醒通知
        await notification_service.notify_follow_reminder(customers)
        
        # 为高优先级客户自动生成跟进内容
        high_priority = [c for c in customers if c.get("intent_level") in ["S", "A"]]
        
        for customer in high_priority[:10]:  # 最多处理10个
            try:
                await _generate_follow_content(customer)
            except Exception as e:
                logger.error(f"生成跟进内容失败 [{customer.get('name')}]: {e}")
        
        logger.info("📅 每日跟进检查完成")
        
    except Exception as e:
        logger.error(f"每日跟进检查失败: {e}")


async def _generate_follow_content(customer: Dict[str, Any]):
    """为客户生成跟进内容"""
    customer_id = customer.get("id")
    customer_name = customer.get("name", "未知")
    
    # 获取最近对话
    chat_history = await conversation_service.get_chat_history(customer_id, limit=5)
    last_conversation = "\n".join([
        f"[{h['message_type']}] {h['content']}" for h in chat_history
    ]) if chat_history else "无历史对话"
    
    # 调用小跟生成跟进内容
    try:
        result = await follow_agent.process({
            "customer_info": {
                "name": customer_name,
                "company": customer.get("company")
            },
            "intent_level": customer.get("intent_level", "B"),
            "last_contact": customer.get("last_contact_at", "未知"),
            "last_conversation": last_conversation,
            "purpose": "日常跟进"
        })
        
        follow_message = result.get("follow_message", "")
        
        if follow_message:
            # 保存跟进记录
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        INSERT INTO follow_records 
                        (customer_id, follow_type, channel, executor_type, executor_name, 
                         content, intent_before, intent_after, created_at)
                        VALUES (:customer_id, 'daily_follow', 'system', 'follow', '小跟',
                                :content, :intent_score, :intent_score, NOW())
                    """),
                    {
                        "customer_id": customer_id,
                        "content": follow_message,
                        "intent_score": customer.get("intent_score", 0)
                    }
                )
                await db.commit()
            
            logger.info(f"📅 已为 {customer_name} 生成跟进内容")
            
    except Exception as e:
        logger.error(f"生成跟进内容失败: {e}")


async def check_no_reply_customers():
    """
    检查未回复客户
    对于发送消息后超过一定时间未回复的客户进行标记
    """
    logger.info("📅 开始执行: 未回复客户检查")
    
    try:
        async with async_session_maker() as db:
            # 查找24小时内发送了消息但未收到回复的客户
            result = await db.execute(
                text("""
                    WITH last_outbound AS (
                        SELECT customer_id, MAX(created_at) as last_sent_at
                        FROM conversations
                        WHERE message_type = 'outbound'
                        AND created_at > NOW() - INTERVAL '24 hours'
                        GROUP BY customer_id
                    ),
                    last_inbound AS (
                        SELECT customer_id, MAX(created_at) as last_received_at
                        FROM conversations
                        WHERE message_type = 'inbound'
                        GROUP BY customer_id
                    )
                    SELECT 
                        c.id, c.name, c.intent_level,
                        lo.last_sent_at,
                        li.last_received_at
                    FROM customers c
                    JOIN last_outbound lo ON c.id = lo.customer_id
                    LEFT JOIN last_inbound li ON c.id = li.customer_id
                    WHERE (li.last_received_at IS NULL OR li.last_received_at < lo.last_sent_at)
                    AND lo.last_sent_at < NOW() - INTERVAL '4 hours'
                """)
            )
            rows = result.fetchall()
            
            no_reply_count = len(rows)
            
            if no_reply_count > 0:
                logger.info(f"📅 发现 {no_reply_count} 位客户未回复")
                
                # 更新跟进记录的结果
                for row in rows:
                    customer_id = row[0]
                    await db.execute(
                        text("""
                            UPDATE follow_records
                            SET result = 'no_reply'
                            WHERE customer_id = :customer_id
                            AND result IS NULL
                            AND created_at > NOW() - INTERVAL '24 hours'
                        """),
                        {"customer_id": customer_id}
                    )
                
                await db.commit()
            else:
                logger.info("📅 没有未回复的客户")
        
    except Exception as e:
        logger.error(f"未回复客户检查失败: {e}")


async def daily_summary_task():
    """
    每日工作汇总任务
    统计今日数据并发送汇总通知
    """
    logger.info("📅 开始执行: 每日工作汇总")
    
    try:
        # 获取今日统计数据
        new_customers = await conversation_service.get_customer_count(today_only=True)
        high_intent = await conversation_service.get_high_intent_count(today_only=True)
        conversations = await conversation_service.get_conversation_count(today_only=True)
        
        # 获取今日跟进次数
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM follow_records
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
            )
            follow_count = result.scalar() or 0
            
            # 获取今日视频生成数
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM videos
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
            )
            videos_count = result.scalar() or 0
            
            # 获取今日高意向客户列表
            result = await db.execute(
                text("""
                    SELECT name, company, intent_level, intent_score
                    FROM customers
                    WHERE intent_level IN ('S', 'A')
                    AND DATE(updated_at) = CURRENT_DATE
                    ORDER BY intent_score DESC
                    LIMIT 10
                """)
            )
            top_customers = [
                {
                    "name": row[0],
                    "company": row[1],
                    "intent_level": row[2],
                    "intent_score": row[3]
                }
                for row in result.fetchall()
            ]
        
        logger.info(f"📅 今日统计: 新客户={new_customers}, 高意向={high_intent}, 对话={conversations}, 跟进={follow_count}")
        
        # 发送汇总通知
        await notification_service.notify_daily_summary(
            new_customers=new_customers,
            high_intent_count=high_intent,
            conversations=conversations,
            follow_count=follow_count,
            videos_generated=videos_count,
            top_customers=top_customers
        )
        
        logger.info("📅 每日工作汇总完成")
        
    except Exception as e:
        logger.error(f"每日工作汇总失败: {e}")


async def reset_daily_stats():
    """
    重置每日统计
    每天凌晨重置AI员工的今日任务数
    """
    logger.info("📅 开始执行: 重置每日统计")
    
    try:
        async with async_session_maker() as db:
            await db.execute(
                text("""
                    UPDATE ai_agents
                    SET tasks_completed_today = 0,
                        updated_at = NOW()
                """)
            )
            await db.commit()
        
        logger.info("📅 每日统计已重置")
        
    except Exception as e:
        logger.error(f"重置每日统计失败: {e}")


async def trigger_customer_follow(
    customer_id: str,
    reason: str = "event_trigger"
):
    """
    事件驱动的跟进触发
    当特定事件发生时触发跟进
    
    Args:
        customer_id: 客户ID
        reason: 触发原因
    """
    logger.info(f"📅 事件触发跟进: customer={customer_id}, reason={reason}")
    
    try:
        # 获取客户信息
        customer = await conversation_service.get_customer_info(customer_id)
        
        if not customer:
            logger.warning(f"客户不存在: {customer_id}")
            return
        
        # 生成跟进内容
        await _generate_follow_content(customer)
        
    except Exception as e:
        logger.error(f"事件触发跟进失败: {e}")


# 事件触发器：可以被其他模块调用
class FollowEventTrigger:
    """跟进事件触发器"""
    
    @staticmethod
    async def on_intent_drop(customer_id: str, old_level: str, new_level: str):
        """当客户意向下降时触发"""
        if old_level in ["S", "A"] and new_level in ["B", "C"]:
            await trigger_customer_follow(customer_id, "intent_drop")
    
    @staticmethod
    async def on_no_contact(customer_id: str, days: int):
        """当客户长时间未联系时触发"""
        if days >= 7:
            await trigger_customer_follow(customer_id, f"no_contact_{days}days")
    
    @staticmethod
    async def on_lead_created(lead_id: str, customer_id: str):
        """当新线索创建时触发首次跟进"""
        await trigger_customer_follow(customer_id, "new_lead")


follow_trigger = FollowEventTrigger()
