"""
自动化营销序列服务
支持新线索培育序列和老客户维护序列
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.services.timezone_service import timezone_service


# 默认营销序列配置
DEFAULT_SEQUENCES = {
    "new_lead_nurture": {
        "name": "新线索培育序列",
        "description": "对新进入的线索进行自动培育",
        "trigger_event": "new_lead",
        "steps": [
            {
                "step": 1,
                "action": "send_welcome",
                "delay_hours": 0,
                "content_template": "欢迎消息+公司介绍",
                "executor": "sales"
            },
            {
                "step": 2,
                "action": "ask_needs",
                "delay_hours": 1,
                "content_template": "主动询问需求",
                "executor": "sales",
                "condition": "no_reply"
            },
            {
                "step": 3,
                "action": "follow_quote",
                "delay_hours": 24,
                "content_template": "跟进报价反馈",
                "executor": "follow",
                "condition": "quote_sent"
            },
            {
                "step": 4,
                "action": "send_case",
                "delay_hours": 48,
                "content_template": "发送成功案例",
                "executor": "follow",
                "condition": "hesitating"
            },
            {
                "step": 5,
                "action": "send_news",
                "delay_hours": 168,  # 7天
                "content_template": "发送行业资讯",
                "executor": "follow",
                "condition": "no_interaction"
            }
        ]
    },
    "customer_retention": {
        "name": "老客户维护序列",
        "description": "维护老客户关系，促进复购",
        "trigger_event": "customer_idle",
        "steps": [
            {
                "step": 1,
                "action": "repurchase_remind",
                "delay_hours": 0,
                "content_template": "复购提醒",
                "executor": "follow",
                "condition": "near_purchase_cycle"
            },
            {
                "step": 2,
                "action": "price_drop_notify",
                "delay_hours": 0,
                "content_template": "运价下降通知",
                "executor": "follow",
                "condition": "price_dropped"
            },
            {
                "step": 3,
                "action": "holiday_greeting",
                "delay_hours": 0,
                "content_template": "节假日祝福",
                "executor": "follow",
                "condition": "holiday"
            },
            {
                "step": 4,
                "action": "churn_prevention",
                "delay_hours": 72,
                "content_template": "关怀回访",
                "executor": "follow",
                "condition": "interaction_decreased"
            }
        ]
    },
    "quote_followup": {
        "name": "报价跟进序列",
        "description": "报价后的自动跟进",
        "trigger_event": "quote_sent",
        "steps": [
            {
                "step": 1,
                "action": "quote_confirm",
                "delay_hours": 4,
                "content_template": "确认报价是否收到",
                "executor": "follow"
            },
            {
                "step": 2,
                "action": "quote_feedback",
                "delay_hours": 24,
                "content_template": "询问报价反馈",
                "executor": "follow",
                "condition": "no_reply"
            },
            {
                "step": 3,
                "action": "competitor_compare",
                "delay_hours": 48,
                "content_template": "提供价格对比优势",
                "executor": "sales",
                "condition": "comparing"
            },
            {
                "step": 4,
                "action": "urgency_create",
                "delay_hours": 72,
                "content_template": "创造紧迫感",
                "executor": "sales",
                "condition": "still_hesitating"
            }
        ]
    }
}


class MarketingSequenceService:
    """营销序列服务"""
    
    def __init__(self):
        pass
    
    async def init_default_sequences(self):
        """初始化默认营销序列"""
        try:
            async with async_session_maker() as db:
                for seq_key, seq_data in DEFAULT_SEQUENCES.items():
                    await db.execute(
                        text("""
                            INSERT INTO marketing_sequences 
                            (name, description, trigger_event, sequence_steps, is_active, created_at, updated_at)
                            VALUES (:name, :desc, :trigger, :steps, true, NOW(), NOW())
                            ON CONFLICT (name) DO NOTHING
                        """),
                        {
                            "name": seq_data["name"],
                            "desc": seq_data["description"],
                            "trigger": seq_data["trigger_event"],
                            "steps": json.dumps(seq_data["steps"], ensure_ascii=False)
                        }
                    )
                await db.commit()
                
            logger.info(f"📧 初始化 {len(DEFAULT_SEQUENCES)} 个营销序列")
            
        except Exception as e:
            logger.error(f"初始化营销序列失败: {e}")
    
    async def trigger_sequence(
        self,
        sequence_name: str,
        customer_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        触发营销序列
        
        Args:
            sequence_name: 序列名称或触发事件
            customer_id: 客户ID
            lead_id: 线索ID
            context: 上下文信息
        
        Returns:
            序列执行记录ID
        """
        try:
            async with async_session_maker() as db:
                # 查找序列
                result = await db.execute(
                    text("""
                        SELECT id, sequence_steps FROM marketing_sequences
                        WHERE (name = :name OR trigger_event = :name)
                        AND is_active = true
                    """),
                    {"name": sequence_name}
                )
                row = result.fetchone()
                
                if not row:
                    logger.warning(f"营销序列不存在或未激活: {sequence_name}")
                    return None
                
                sequence_id = row[0]
                steps = row[1] if isinstance(row[1], list) else json.loads(row[1])
                
                # 检查是否已有进行中的序列
                result = await db.execute(
                    text("""
                        SELECT id FROM marketing_sequence_logs
                        WHERE sequence_id = :seq_id
                        AND (customer_id = :customer_id OR lead_id = :lead_id)
                        AND status = 'active'
                    """),
                    {
                        "seq_id": sequence_id,
                        "customer_id": customer_id,
                        "lead_id": lead_id
                    }
                )
                
                if result.fetchone():
                    logger.info(f"已有进行中的序列，跳过触发")
                    return None
                
                # 计算第一步的执行时间
                first_step = steps[0] if steps else None
                if not first_step:
                    return None
                
                delay_hours = first_step.get("delay_hours", 0)
                next_action_at = datetime.now() + timedelta(hours=delay_hours)
                
                # 创建序列执行记录
                result = await db.execute(
                    text("""
                        INSERT INTO marketing_sequence_logs 
                        (sequence_id, customer_id, lead_id, current_step, status,
                         next_action_at, executed_steps, created_at, updated_at)
                        VALUES (:seq_id, :customer_id, :lead_id, 0, 'active',
                                :next_action, '[]'::jsonb, NOW(), NOW())
                        RETURNING id
                    """),
                    {
                        "seq_id": sequence_id,
                        "customer_id": customer_id,
                        "lead_id": lead_id,
                        "next_action": next_action_at
                    }
                )
                log_id = result.fetchone()[0]
                await db.commit()
                
                logger.info(f"📧 触发营销序列: {sequence_name}, 记录ID: {log_id}")
                return str(log_id)
                
        except Exception as e:
            logger.error(f"触发营销序列失败: {e}")
            return None
    
    async def process_pending_actions(self):
        """
        处理待执行的营销动作
        由定时任务调用
        """
        try:
            async with async_session_maker() as db:
                # 获取需要执行的动作
                result = await db.execute(
                    text("""
                        SELECT 
                            l.id, l.sequence_id, l.customer_id, l.lead_id,
                            l.current_step, l.executed_steps,
                            s.sequence_steps
                        FROM marketing_sequence_logs l
                        JOIN marketing_sequences s ON l.sequence_id = s.id
                        WHERE l.status = 'active'
                        AND l.next_action_at <= NOW()
                        LIMIT 50
                    """)
                )
                pending_logs = result.fetchall()
                
                processed = 0
                for log in pending_logs:
                    log_id = log[0]
                    customer_id = log[2]
                    lead_id = log[3]
                    current_step = log[4]
                    executed_steps = log[5] or []
                    sequence_steps = log[6] if isinstance(log[6], list) else json.loads(log[6])
                    
                    # 检查时区（如果有客户ID）
                    if customer_id:
                        dnd_check = await timezone_service.check_customer_dnd(str(customer_id))
                        if dnd_check.get("is_dnd"):
                            # 在免打扰时间，延迟到下一个可联系时间
                            next_time = dnd_check.get("next_available")
                            await db.execute(
                                text("""
                                    UPDATE marketing_sequence_logs
                                    SET next_action_at = :next_time
                                    WHERE id = :id
                                """),
                                {"id": log_id, "next_time": next_time}
                            )
                            continue
                    
                    # 获取当前步骤
                    if current_step >= len(sequence_steps):
                        # 序列已完成
                        await db.execute(
                            text("""
                                UPDATE marketing_sequence_logs
                                SET status = 'completed', updated_at = NOW()
                                WHERE id = :id
                            """),
                            {"id": log_id}
                        )
                        continue
                    
                    step = sequence_steps[current_step]
                    
                    # 执行动作
                    success = await self._execute_step(
                        step=step,
                        customer_id=customer_id,
                        lead_id=lead_id
                    )
                    
                    # 更新执行记录
                    executed_steps.append({
                        "step": current_step,
                        "action": step.get("action"),
                        "executed_at": datetime.now().isoformat(),
                        "success": success
                    })
                    
                    # 计算下一步执行时间
                    next_step = current_step + 1
                    if next_step < len(sequence_steps):
                        next_step_data = sequence_steps[next_step]
                        delay_hours = next_step_data.get("delay_hours", 24)
                        next_action_at = datetime.now() + timedelta(hours=delay_hours)
                        status = 'active'
                    else:
                        next_action_at = None
                        status = 'completed'
                    
                    await db.execute(
                        text("""
                            UPDATE marketing_sequence_logs
                            SET current_step = :step,
                                executed_steps = :executed,
                                next_action_at = :next_time,
                                status = :status,
                                updated_at = NOW()
                            WHERE id = :id
                        """),
                        {
                            "id": log_id,
                            "step": next_step,
                            "executed": json.dumps(executed_steps, ensure_ascii=False),
                            "next_time": next_action_at,
                            "status": status
                        }
                    )
                    
                    processed += 1
                
                await db.commit()
                
                if processed > 0:
                    logger.info(f"📧 处理了 {processed} 个营销动作")
                
                return {"processed": processed}
                
        except Exception as e:
            logger.error(f"处理营销动作失败: {e}")
            return {"error": str(e)}
    
    async def _execute_step(
        self,
        step: Dict[str, Any],
        customer_id: Optional[str],
        lead_id: Optional[str]
    ) -> bool:
        """执行单个营销步骤"""
        action = step.get("action")
        executor = step.get("executor", "follow")
        content_template = step.get("content_template", "")
        
        try:
            # 根据执行者调用对应的Agent
            if executor == "sales":
                from app.agents.sales_agent import sales_agent
                await sales_agent.process({
                    "customer_id": customer_id,
                    "lead_id": lead_id,
                    "action": action,
                    "template": content_template
                })
            elif executor == "follow":
                from app.agents.follow_agent import follow_agent
                await follow_agent.process({
                    "customer_id": customer_id,
                    "purpose": action,
                    "template": content_template
                })
            
            logger.info(f"📧 执行营销动作: {action} -> {executor}")
            return True
            
        except Exception as e:
            logger.error(f"执行营销步骤失败: {e}")
            return False
    
    async def pause_sequence(self, log_id: str) -> bool:
        """暂停序列"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE marketing_sequence_logs
                        SET status = 'paused', updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": log_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"暂停序列失败: {e}")
            return False
    
    async def resume_sequence(self, log_id: str) -> bool:
        """恢复序列"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE marketing_sequence_logs
                        SET status = 'active',
                            next_action_at = NOW(),
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": log_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"恢复序列失败: {e}")
            return False
    
    async def cancel_sequence(self, log_id: str) -> bool:
        """取消序列"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("""
                        UPDATE marketing_sequence_logs
                        SET status = 'cancelled', updated_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": log_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"取消序列失败: {e}")
            return False
    
    async def get_active_sequences(
        self,
        customer_id: Optional[str] = None,
        lead_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取活跃的序列"""
        try:
            async with async_session_maker() as db:
                query = """
                    SELECT 
                        l.id, s.name, l.current_step, l.status,
                        l.next_action_at, l.created_at
                    FROM marketing_sequence_logs l
                    JOIN marketing_sequences s ON l.sequence_id = s.id
                    WHERE l.status IN ('active', 'paused')
                """
                params = {}
                
                if customer_id:
                    query += " AND l.customer_id = :customer_id"
                    params["customer_id"] = customer_id
                
                if lead_id:
                    query += " AND l.lead_id = :lead_id"
                    params["lead_id"] = lead_id
                
                query += " ORDER BY l.created_at DESC"
                
                result = await db.execute(text(query), params)
                
                return [
                    {
                        "id": str(row[0]),
                        "sequence_name": row[1],
                        "current_step": row[2],
                        "status": row[3],
                        "next_action_at": row[4].isoformat() if row[4] else None,
                        "created_at": row[5].isoformat() if row[5] else None
                    }
                    for row in result.fetchall()
                ]
        except Exception as e:
            logger.error(f"获取活跃序列失败: {e}")
            return []


# 创建单例
marketing_sequence = MarketingSequenceService()
