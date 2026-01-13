"""
对话API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.models import get_db, Conversation, Customer, AgentType, MessageType

router = APIRouter()


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


@router.post("/send")
async def send_message(
    customer_id: UUID,
    content: str,
    agent_type: AgentType = AgentType.SALES,
    db: AsyncSession = Depends(get_db)
):
    """
    发送消息给客户（由AI员工处理）
    这个接口会触发AI员工生成回复
    """
    # 验证客户存在
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 记录客户消息
    inbound_msg = Conversation(
        customer_id=customer_id,
        agent_type=agent_type,
        message_type=MessageType.INBOUND,
        content=content,
        session_id=f"session_{customer_id}_{datetime.utcnow().strftime('%Y%m%d')}"
    )
    db.add(inbound_msg)
    
    # TODO: 这里会调用对应的AI员工生成回复
    # 现在先返回一个占位回复
    ai_reply = f"[{agent_type.value}] 收到您的消息，正在处理中..."
    
    outbound_msg = Conversation(
        customer_id=customer_id,
        agent_type=agent_type,
        message_type=MessageType.OUTBOUND,
        content=ai_reply,
        session_id=inbound_msg.session_id
    )
    db.add(outbound_msg)
    
    await db.commit()
    
    return {
        "status": "sent",
        "customer_id": str(customer_id),
        "agent": agent_type.value,
        "reply": ai_reply
    }
