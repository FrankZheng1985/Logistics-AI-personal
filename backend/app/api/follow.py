"""
跟进记录管理API
CRM系统核心功能：记录、查询、管理客户跟进轨迹
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from pydantic import BaseModel
from loguru import logger

from app.models import (
    get_db, 
    Customer, 
    FollowRecord, 
    FollowType, 
    FollowResult, 
    FollowChannel
)
from app.agents.follow_agent import follow_agent

router = APIRouter()


# =====================================================
# 请求/响应模型
# =====================================================

class FollowRecordCreate(BaseModel):
    """创建跟进记录请求"""
    customer_id: UUID
    follow_type: FollowType = FollowType.DAILY_FOLLOW
    channel: FollowChannel = FollowChannel.WECHAT
    content: str
    executor_type: str = "manual"  # sales/follow/manual
    executor_name: Optional[str] = None
    result: Optional[FollowResult] = None
    result_note: Optional[str] = None
    next_follow_at: Optional[datetime] = None
    next_follow_note: Optional[str] = None


class FollowRecordUpdate(BaseModel):
    """更新跟进记录请求"""
    customer_reply: Optional[str] = None
    result: Optional[FollowResult] = None
    result_note: Optional[str] = None
    next_follow_at: Optional[datetime] = None
    next_follow_note: Optional[str] = None


class AIFollowRequest(BaseModel):
    """AI自动跟进请求"""
    customer_id: UUID
    follow_type: FollowType = FollowType.DAILY_FOLLOW
    channel: FollowChannel = FollowChannel.WECHAT
    purpose: Optional[str] = "日常跟进"


class AIFollowWithEmailRequest(BaseModel):
    """AI跟进并发送邮件请求"""
    customer_id: UUID
    purpose: str = "daily_follow"  # daily_follow, quote_follow, reactivate
    custom_content: Optional[str] = None  # 自定义内容（可选）


# =====================================================
# API端点
# =====================================================

@router.get("")
async def list_follow_records(
    customer_id: Optional[UUID] = None,
    follow_type: Optional[FollowType] = None,
    result: Optional[FollowResult] = None,
    executor_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取跟进记录列表"""
    query = select(FollowRecord)
    
    # 过滤条件
    if customer_id:
        query = query.where(FollowRecord.customer_id == customer_id)
    if follow_type:
        query = query.where(FollowRecord.follow_type == follow_type)
    if result:
        query = query.where(FollowRecord.result == result)
    if executor_type:
        query = query.where(FollowRecord.executor_type == executor_type)
    if start_date:
        query = query.where(FollowRecord.created_at >= start_date)
    if end_date:
        query = query.where(FollowRecord.created_at <= end_date)
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.order_by(FollowRecord.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(r.id),
                "customer_id": str(r.customer_id),
                "follow_type": r.follow_type.value,
                "channel": r.channel.value,
                "executor_type": r.executor_type,
                "executor_name": r.executor_name,
                "content": r.content,
                "customer_reply": r.customer_reply,
                "result": r.result.value if r.result else None,
                "result_note": r.result_note,
                "intent_before": r.intent_before,
                "intent_after": r.intent_after,
                "intent_delta": r.intent_after - r.intent_before,
                "next_follow_at": r.next_follow_at.isoformat() if r.next_follow_at else None,
                "next_follow_note": r.next_follow_note,
                "created_at": r.created_at.isoformat()
            }
            for r in records
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/customer/{customer_id}/timeline")
async def get_customer_follow_timeline(
    customer_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """获取客户跟进时间线（按时间正序）"""
    # 验证客户存在
    customer_result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 获取跟进记录
    result = await db.execute(
        select(FollowRecord)
        .where(FollowRecord.customer_id == customer_id)
        .order_by(FollowRecord.created_at.asc())
        .limit(limit)
    )
    records = result.scalars().all()
    
    return {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "company": customer.company,
            "intent_level": customer.intent_level.value,
            "intent_score": customer.intent_score
        },
        "timeline": [
            {
                "id": str(r.id),
                "follow_type": r.follow_type.value,
                "channel": r.channel.value,
                "executor": f"{r.executor_type}:{r.executor_name}" if r.executor_name else r.executor_type,
                "content": r.content,
                "customer_reply": r.customer_reply,
                "result": r.result.value if r.result else None,
                "intent_change": f"{r.intent_before} -> {r.intent_after}" if r.intent_after != r.intent_before else None,
                "timestamp": r.created_at.isoformat()
            }
            for r in records
        ],
        "total_follows": len(records)
    }


@router.get("/today-tasks")
async def get_today_follow_tasks(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取今日待跟进任务"""
    # 使用原生SQL查询视图
    result = await db.execute(
        text("""
            SELECT 
                c.id as customer_id,
                c.name as customer_name,
                c.company,
                c.phone,
                c.wechat_id,
                c.intent_level,
                c.intent_score,
                c.last_contact_at,
                c.next_follow_at,
                CASE 
                    WHEN c.intent_level = 'S' THEN 1
                    WHEN c.intent_level = 'A' THEN 2
                    WHEN c.intent_level = 'B' THEN 3
                    ELSE 4
                END as priority
            FROM customers c
            WHERE c.is_active = true
            AND (
                (c.next_follow_at IS NOT NULL AND DATE(c.next_follow_at) <= CURRENT_DATE)
                OR (
                    c.next_follow_at IS NULL 
                    AND c.last_contact_at IS NOT NULL
                    AND (
                        (c.intent_level = 'S' AND c.last_contact_at < NOW() - INTERVAL '1 day')
                        OR (c.intent_level = 'A' AND c.last_contact_at < NOW() - INTERVAL '2 days')
                        OR (c.intent_level = 'B' AND c.last_contact_at < NOW() - INTERVAL '5 days')
                        OR (c.intent_level = 'C' AND c.last_contact_at < NOW() - INTERVAL '15 days')
                    )
                )
            )
            ORDER BY priority, c.last_contact_at ASC
            LIMIT :limit
        """),
        {"limit": limit}
    )
    rows = result.fetchall()
    
    return {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "tasks": [
            {
                "customer_id": str(row[0]),
                "customer_name": row[1],
                "company": row[2],
                "phone": row[3],
                "wechat_id": row[4],
                "intent_level": row[5],
                "intent_score": row[6],
                "last_contact_at": row[7].isoformat() if row[7] else None,
                "next_follow_at": row[8].isoformat() if row[8] else None,
                "priority": row[9]
            }
            for row in rows
        ],
        "total": len(rows)
    }


@router.get("/stats")
async def get_follow_stats(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """获取跟进统计数据"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # 总跟进次数
    total_result = await db.execute(
        select(func.count(FollowRecord.id))
        .where(FollowRecord.created_at >= start_date)
    )
    total = total_result.scalar() or 0
    
    # 按结果统计
    result_stats = {}
    for fr in FollowResult:
        result = await db.execute(
            select(func.count(FollowRecord.id))
            .where(and_(
                FollowRecord.created_at >= start_date,
                FollowRecord.result == fr
            ))
        )
        count = result.scalar() or 0
        if count > 0:
            result_stats[fr.value] = count
    
    # 按执行者统计
    executor_result = await db.execute(
        text("""
            SELECT executor_type, COUNT(*) as count
            FROM follow_records
            WHERE created_at >= :start_date
            GROUP BY executor_type
        """),
        {"start_date": start_date}
    )
    executor_stats = {row[0]: row[1] for row in executor_result.fetchall()}
    
    # 今日统计
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(FollowRecord.id))
        .where(FollowRecord.created_at >= today)
    )
    today_count = today_result.scalar() or 0
    
    # 回复率
    replied_count = result_stats.get("replied", 0) + result_stats.get("interested", 0) + result_stats.get("deal_progress", 0)
    reply_rate = round(replied_count / total * 100, 1) if total > 0 else 0
    
    return {
        "period_days": days,
        "total_follows": total,
        "today_follows": today_count,
        "reply_rate": reply_rate,
        "by_result": result_stats,
        "by_executor": executor_stats
    }


@router.post("")
async def create_follow_record(
    data: FollowRecordCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建跟进记录（手动）"""
    # 验证客户存在
    customer_result = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 创建记录
    record = FollowRecord(
        customer_id=data.customer_id,
        follow_type=data.follow_type,
        channel=data.channel,
        executor_type=data.executor_type,
        executor_name=data.executor_name,
        content=data.content,
        result=data.result,
        result_note=data.result_note,
        intent_before=customer.intent_score,
        intent_after=customer.intent_score,
        intent_level_before=customer.intent_level.value,
        intent_level_after=customer.intent_level.value,
        next_follow_at=data.next_follow_at,
        next_follow_note=data.next_follow_note
    )
    
    db.add(record)
    
    # 更新客户信息
    customer.last_contact_at = datetime.utcnow()
    customer.follow_count += 1
    if data.next_follow_at:
        customer.next_follow_at = data.next_follow_at
    
    await db.commit()
    await db.refresh(record)
    
    logger.info(f"创建跟进记录: 客户={customer.name}, 类型={data.follow_type.value}")
    
    return {
        "id": str(record.id),
        "message": "跟进记录创建成功"
    }


@router.post("/ai-follow")
async def create_ai_follow(
    data: AIFollowRequest,
    db: AsyncSession = Depends(get_db)
):
    """AI自动生成跟进内容并记录"""
    # 验证客户存在
    customer_result = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 获取最近对话
    from app.models import Conversation
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.customer_id == data.customer_id)
        .order_by(Conversation.created_at.desc())
        .limit(5)
    )
    conversations = conv_result.scalars().all()
    last_conversation = "\n".join([
        f"[{c.message_type.value}] {c.content}" for c in reversed(conversations)
    ]) if conversations else "无历史对话"
    
    # 调用小跟生成跟进内容
    try:
        follow_result = await follow_agent.process({
            "customer_info": {
                "name": customer.name,
                "company": customer.company,
                "phone": customer.phone
            },
            "intent_level": customer.intent_level.value,
            "last_contact": customer.last_contact_at.isoformat() if customer.last_contact_at else "从未联系",
            "last_conversation": last_conversation,
            "purpose": data.purpose
        })
        
        follow_message = follow_result.get("follow_message", "您好，有什么可以帮您的吗？")
        next_follow_time = follow_result.get("next_follow_time")
        suggested_interval = follow_result.get("suggested_interval_days", 3)
        
    except Exception as e:
        logger.error(f"AI生成跟进内容失败: {e}")
        follow_message = f"您好，我是{customer.company or '贵公司'}的物流顾问，想跟您确认一下物流需求..."
        next_follow_time = None
        suggested_interval = 3
    
    # 创建跟进记录
    record = FollowRecord(
        customer_id=data.customer_id,
        follow_type=data.follow_type,
        channel=data.channel,
        executor_type="follow",
        executor_name="小跟",
        content=follow_message,
        intent_before=customer.intent_score,
        intent_after=customer.intent_score,
        intent_level_before=customer.intent_level.value,
        intent_level_after=customer.intent_level.value,
        next_follow_at=datetime.fromisoformat(next_follow_time) if next_follow_time else datetime.utcnow() + timedelta(days=suggested_interval)
    )
    
    db.add(record)
    
    # 更新客户
    customer.last_contact_at = datetime.utcnow()
    customer.follow_count += 1
    customer.next_follow_at = record.next_follow_at
    
    await db.commit()
    await db.refresh(record)
    
    logger.info(f"AI跟进记录创建: 客户={customer.name}, 内容={follow_message[:30]}...")
    
    return {
        "id": str(record.id),
        "follow_message": follow_message,
        "next_follow_at": record.next_follow_at.isoformat() if record.next_follow_at else None,
        "message": "AI跟进内容已生成"
    }


@router.post("/ai-follow-email")
async def ai_follow_with_email(
    data: AIFollowWithEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    AI自动跟进 + 发送邮件
    
    小跟生成跟进内容后，自动发送邮件给客户
    """
    from app.services.email_service import email_service
    
    # 验证客户存在
    customer_result = await db.execute(
        select(Customer).where(Customer.id == data.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    # 检查客户是否有邮箱
    if not customer.email:
        raise HTTPException(status_code=400, detail="客户未设置邮箱地址，无法发送邮件跟进")
    
    # 检查邮件服务是否配置
    if not email_service.is_configured:
        raise HTTPException(status_code=400, detail="邮件服务未配置，请先在设置中配置SMTP")
    
    # 如果有自定义内容，直接使用
    if data.custom_content:
        follow_message = data.custom_content
        suggested_interval = 3
    else:
        # 获取最近对话用于AI生成
        from app.models import Conversation
        conv_result = await db.execute(
            select(Conversation)
            .where(Conversation.customer_id == data.customer_id)
            .order_by(Conversation.created_at.desc())
            .limit(5)
        )
        conversations = conv_result.scalars().all()
        last_conversation = "\n".join([
            f"[{c.message_type.value}] {c.content}" for c in reversed(conversations)
        ]) if conversations else "无历史对话"
        
        # 调用小跟生成跟进内容
        try:
            follow_result = await follow_agent.process({
                "customer_info": {
                    "name": customer.name,
                    "company": customer.company,
                    "phone": customer.phone
                },
                "intent_level": customer.intent_level.value,
                "last_contact": customer.last_contact_at.isoformat() if customer.last_contact_at else "从未联系",
                "last_conversation": last_conversation,
                "purpose": data.purpose
            })
            
            follow_message = follow_result.get("follow_message", "您好，有什么可以帮您的吗？")
            suggested_interval = follow_result.get("suggested_interval_days", 3)
            
        except Exception as e:
            logger.error(f"AI生成跟进内容失败: {e}")
            follow_message = f"您好，我是您的物流顾问，想跟您确认一下物流需求。如有任何问题，请随时联系我们。"
            suggested_interval = 3
    
    # 创建跟进记录
    record = FollowRecord(
        customer_id=data.customer_id,
        follow_type=FollowType.DAILY_FOLLOW,
        channel=FollowChannel.EMAIL,  # 邮件渠道
        executor_type="follow",
        executor_name="小跟",
        content=follow_message,
        intent_before=customer.intent_score,
        intent_after=customer.intent_score,
        intent_level_before=customer.intent_level.value,
        intent_level_after=customer.intent_level.value,
        next_follow_at=datetime.utcnow() + timedelta(days=suggested_interval)
    )
    
    db.add(record)
    await db.flush()  # 获取记录ID
    
    # 发送邮件
    email_result = await email_service.send_follow_email(
        customer_id=str(customer.id),
        to_email=customer.email,
        customer_name=customer.name or "尊敬的客户",
        purpose=data.purpose,
        custom_content=follow_message
    )
    
    # 根据发送结果更新记录
    if email_result.get("status") == "sent":
        record.result = FollowResult.NO_REPLY  # 初始状态为未回复
        
        # 关联邮件日志
        if email_result.get("email_log_id"):
            record.extra_data = {"email_log_id": email_result.get("email_log_id")}
        
        # 更新客户信息
        customer.last_contact_at = datetime.utcnow()
        customer.follow_count += 1
        customer.next_follow_at = record.next_follow_at
        
        await db.commit()
        await db.refresh(record)
        
        logger.info(f"AI邮件跟进成功: 客户={customer.name}, 邮箱={customer.email}")
        
        return {
            "success": True,
            "record_id": str(record.id),
            "follow_message": follow_message,
            "email_sent_to": customer.email,
            "next_follow_at": record.next_follow_at.isoformat() if record.next_follow_at else None,
            "message": f"跟进邮件已发送至 {customer.email}"
        }
    else:
        # 邮件发送失败，但仍保存跟进记录
        record.result_note = f"邮件发送失败: {email_result.get('message', '未知错误')}"
        await db.commit()
        
        return {
            "success": False,
            "record_id": str(record.id),
            "follow_message": follow_message,
            "error": email_result.get("message", "邮件发送失败"),
            "message": "跟进内容已生成但邮件发送失败"
        }


@router.patch("/{record_id}")
async def update_follow_record(
    record_id: UUID,
    data: FollowRecordUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新跟进记录（如客户回复、结果等）"""
    result = await db.execute(
        select(FollowRecord).where(FollowRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="跟进记录不存在")
    
    # 更新字段
    if data.customer_reply is not None:
        record.customer_reply = data.customer_reply
    if data.result is not None:
        record.result = data.result
    if data.result_note is not None:
        record.result_note = data.result_note
    if data.next_follow_at is not None:
        record.next_follow_at = data.next_follow_at
        # 同时更新客户的下次跟进时间
        customer_result = await db.execute(
            select(Customer).where(Customer.id == record.customer_id)
        )
        customer = customer_result.scalar_one_or_none()
        if customer:
            customer.next_follow_at = data.next_follow_at
    if data.next_follow_note is not None:
        record.next_follow_note = data.next_follow_note
    
    await db.commit()
    
    return {"message": "跟进记录更新成功"}


@router.delete("/{record_id}")
async def delete_follow_record(
    record_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """删除跟进记录"""
    result = await db.execute(
        select(FollowRecord).where(FollowRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="跟进记录不存在")
    
    await db.delete(record)
    await db.commit()
    
    return {"message": "跟进记录已删除"}
