"""
对话API - 完整的AI员工对话闭环
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from app.models import get_db, Conversation, Customer, AgentType, MessageType
from app.agents.coordinator import coordinator
from app.agents.sales_agent import sales_agent
from app.agents.follow_agent import follow_agent
from app.agents.analyst import analyst_agent
from app.services.notification import notification_service

router = APIRouter()


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """对话响应"""
    status: str
    customer_id: str
    agent: str
    reply: str
    intent_score: int
    intent_level: str
    intent_delta: int


@router.get("/conversations")
async def list_conversations(
    customer_id: Optional[UUID] = None,
    agent_type: Optional[AgentType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """获取对话列表"""
    query = select(Conversation)
    
    if customer_id:
        query = query.where(Conversation.customer_id == customer_id)
    
    if agent_type:
        query = query.where(Conversation.agent_type == agent_type)
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页和排序
    query = query.order_by(Conversation.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    conversations = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(c.id),
                "customer_id": str(c.customer_id),
                "session_id": c.session_id,
                "agent_type": c.agent_type.value,
                "message_type": c.message_type.value,
                "content": c.content,
                "intent_delta": c.intent_delta,
                "created_at": c.created_at.isoformat()
            }
            for c in conversations
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/customer/{customer_id}/history")
async def get_customer_chat_history(
    customer_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """获取客户对话历史"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .order_by(Conversation.created_at.asc())
        .limit(limit)
    )
    conversations = result.scalars().all()
    
    return {
        "customer_id": str(customer_id),
        "messages": [
            {
                "id": str(c.id),
                "agent_type": c.agent_type.value,
                "type": c.message_type.value,
                "content": c.content,
                "intent_delta": c.intent_delta,
                "timestamp": c.created_at.isoformat()
            }
            for c in conversations
        ]
    }


@router.post("/send/{customer_id}")
async def send_message(
    customer_id: UUID,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """
    发送消息给客户（完整AI员工处理闭环）
    
    流程：
    1. 验证客户存在
    2. 保存客户消息
    3. 小调判断分配给谁处理
    4. AI员工生成回复
    5. 小析分析意向并评分
    6. 更新客户意向
    7. 如果高意向则触发通知
    """
    content = request.content
    
    # 1. 验证客户存在
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 生成会话ID
    session_id = f"session_{customer_id}_{datetime.utcnow().strftime('%Y%m%d')}"
    
    # 2. 保存客户消息（入站）
    inbound_msg = Conversation(
        customer_id=customer_id,
        agent_type=AgentType.SALES,  # 先标记为sales，后面会更新
        message_type=MessageType.INBOUND,
        content=content,
        session_id=session_id
    )
    db.add(inbound_msg)
    await db.flush()
    
    # 3. 判断分配给哪个AI员工
    # 规则：新客户或无历史对话 -> 小销; 老客户 -> 小跟
    is_new_customer = customer.follow_count == 0
    
    if is_new_customer:
        target_agent = sales_agent
        agent_type = AgentType.SALES
        logger.info(f"新客户 {customer.name}，分配给小销处理")
    else:
        target_agent = follow_agent
        agent_type = AgentType.FOLLOW
        logger.info(f"老客户 {customer.name}，分配给小跟处理")
    
    # 更新入站消息的agent_type
    inbound_msg.agent_type = agent_type
    
    # 4. 获取对话历史作为上下文
    history_result = await db.execute(
        select(Conversation)
        .where(Conversation.customer_id == customer_id)
        .order_by(Conversation.created_at.desc())
        .limit(10)
    )
    history = history_result.scalars().all()
    
    chat_history = "\n".join([
        f"[{'客户' if h.message_type == MessageType.INBOUND else 'AI'}] {h.content}"
        for h in reversed(history)
    ])
    
    # 5. AI员工处理消息
    try:
        customer_info = f"姓名: {customer.name or '未知'}, 公司: {customer.company or '未知'}, 意向等级: {customer.intent_level.value}"
        
        response = await target_agent.process({
            "customer_id": str(customer_id),
            "message": content,
            "customer_info": customer_info,
            "chat_history": chat_history if chat_history else "无历史对话"
        })
        
        ai_reply = response.get("reply", "感谢您的咨询，我们会尽快回复您！")
        intent_signals = response.get("intent_signals", [])
        
    except Exception as e:
        logger.error(f"AI员工处理失败: {e}")
        ai_reply = "感谢您的咨询！我是物流AI客服，正在为您处理，请稍候..."
        intent_signals = []
    
    # 6. 小析分析意向并评分
    try:
        analysis_result = await analyst_agent.process({
            "customer_info": {
                "name": customer.name,
                "company": customer.company,
                "current_score": customer.intent_score,
                "current_level": customer.intent_level.value
            },
            "conversations": [
                {"type": "inbound", "content": content},
                {"type": "outbound", "content": ai_reply}
            ],
            "intent_signals": intent_signals,
            "current_score": customer.intent_score
        })
        
        intent_delta = analysis_result.get("score_delta", 0)
        new_intent_score = analysis_result.get("intent_score", customer.intent_score)
        new_intent_level = analysis_result.get("intent_level", customer.intent_level.value)
        should_notify = analysis_result.get("should_notify", False)
        
    except Exception as e:
        logger.error(f"意向分析失败: {e}")
        intent_delta = 5  # 默认+5分
        new_intent_score = max(0, customer.intent_score + intent_delta)
        new_intent_level = customer.intent_level.value
        should_notify = False
    
    # 7. 保存AI回复（出站）
    outbound_msg = Conversation(
        customer_id=customer_id,
        agent_type=agent_type,
        message_type=MessageType.OUTBOUND,
        content=ai_reply,
        session_id=session_id,
        intent_delta=intent_delta
    )
    db.add(outbound_msg)
    
    # 8. 更新客户信息
    old_level = customer.intent_level.value
    customer.intent_score = new_intent_score
    customer.update_intent_level()
    customer.last_contact_at = datetime.utcnow()
    customer.follow_count += 1
    
    await db.commit()
    
    # 9. 如果变为高意向客户，触发通知
    if should_notify or (customer.intent_level.value in ['S', 'A'] and old_level not in ['S', 'A']):
        try:
            await notification_service.notify_high_intent_customer(
                customer_id=str(customer_id),
                customer_name=customer.name or "未知客户",
                intent_score=new_intent_score,
                intent_level=customer.intent_level.value,
                key_signals=intent_signals
            )
            logger.info(f"已发送高意向客户通知: {customer.name}")
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
    
    logger.info(f"对话处理完成: 客户={customer.name}, Agent={agent_type.value}, 意向={old_level}->{customer.intent_level.value}")
    
    return ChatResponse(
        status="sent",
        customer_id=str(customer_id),
        agent=agent_type.value,
        reply=ai_reply,
        intent_score=new_intent_score,
        intent_level=customer.intent_level.value,
        intent_delta=intent_delta
    )


@router.post("/simulate")
async def simulate_customer_message(
    customer_name: str = "测试客户",
    message: str = "你好，我想咨询一下海运到美国的价格",
    db: AsyncSession = Depends(get_db)
):
    """
    模拟客户消息（用于测试）
    会自动创建测试客户并发送消息
    """
    from app.models.customer import CustomerSource
    
    # 查找或创建测试客户
    result = await db.execute(
        select(Customer).where(Customer.name == customer_name)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        customer = Customer(
            name=customer_name,
            source=CustomerSource.OTHER,
            source_detail="测试模拟"
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        logger.info(f"创建测试客户: {customer_name}")
    
    # 发送消息
    return await send_message(
        customer_id=customer.id,
        request=SendMessageRequest(content=message),
        db=db
    )
