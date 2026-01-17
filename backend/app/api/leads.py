"""
线索管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from app.models import get_db
from app.models.lead import Lead, LeadSource, LeadStatus, LeadIntentLevel

router = APIRouter()


# 请求体模型
class LeadCreate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat: Optional[str] = None
    source: LeadSource = LeadSource.MANUAL
    source_url: Optional[str] = None
    source_content: Optional[str] = None
    needs: List[str] = []
    tags: List[str] = []


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat: Optional[str] = None
    status: Optional[LeadStatus] = None
    intent_level: Optional[LeadIntentLevel] = None
    needs: Optional[List[str]] = None
    tags: Optional[List[str]] = None


@router.get("")
async def list_leads(
    status: Optional[LeadStatus] = None,
    intent_level: Optional[LeadIntentLevel] = None,
    source: Optional[LeadSource] = None,
    search: Optional[str] = None,
    include_converted: bool = Query(False, description="是否包含已转化的线索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取线索列表
    
    默认不显示已转化(converted)的线索，如需查看历史转化记录：
    - 设置 include_converted=true 或
    - 设置 status=converted
    """
    query = select(Lead)
    
    # 过滤条件
    if status:
        # 如果明确指定了状态，按指定状态过滤
        query = query.where(Lead.status == status)
    elif not include_converted:
        # 如果没有指定状态且不包含已转化，则排除已转化和无效的线索
        query = query.where(Lead.status.notin_([LeadStatus.CONVERTED, LeadStatus.INVALID]))
    
    if intent_level:
        query = query.where(Lead.intent_level == intent_level)
    if source:
        query = query.where(Lead.source == source)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Lead.name.ilike(search_filter)) |
            (Lead.company.ilike(search_filter)) |
            (Lead.phone.ilike(search_filter)) |
            (Lead.email.ilike(search_filter))
        )
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.order_by(Lead.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(lead.id),
                "name": lead.name,
                "company": lead.company,
                "phone": lead.phone,
                "email": lead.email,
                "wechat": lead.wechat,
                "source": lead.source.value,
                "status": lead.status.value,
                "intent_level": lead.intent_level.value,
                "intent_score": lead.intent_score,
                "ai_summary": lead.ai_summary,
                "needs": lead.needs or [],
                "tags": lead.tags or [],
                "created_at": lead.created_at.isoformat()
            }
            for lead in leads
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stats")
async def get_lead_stats(
    db: AsyncSession = Depends(get_db)
):
    """获取线索统计"""
    # 总线索数
    total_result = await db.execute(select(func.count(Lead.id)))
    total = total_result.scalar()
    
    # 今日新增
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(Lead.id)).where(Lead.created_at >= today)
    )
    today_count = today_result.scalar()
    
    # 按状态统计 - 使用原生SQL避免枚举转换问题
    from sqlalchemy import text
    status_stats = {}
    for status in LeadStatus:
        result = await db.execute(
            text("SELECT count(id) FROM leads WHERE status = :status"),
            {"status": status.value}
        )
        status_stats[status.value] = result.scalar() or 0
    
    # 按意向等级统计
    intent_stats = {}
    for level in LeadIntentLevel:
        result = await db.execute(
            text("SELECT count(id) FROM leads WHERE intent_level = :level"),
            {"level": level.value}
        )
        intent_stats[level.value] = result.scalar() or 0
    
    # 按来源统计
    source_stats = {}
    for src in LeadSource:
        result = await db.execute(
            text("SELECT count(id) FROM leads WHERE source = :source"),
            {"source": src.value}
        )
        count = result.scalar() or 0
        if count > 0:
            source_stats[src.value] = count
    
    return {
        "total": total,
        "today": today_count,
        "by_status": status_stats,
        "by_intent": intent_stats,
        "by_source": source_stats
    }


@router.get("/{lead_id}")
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取线索详情"""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    
    return {
        "id": str(lead.id),
        "name": lead.name,
        "company": lead.company,
        "phone": lead.phone,
        "email": lead.email,
        "wechat": lead.wechat,
        "source": lead.source.value,
        "source_url": lead.source_url,
        "source_content": lead.source_content,
        "status": lead.status.value,
        "intent_level": lead.intent_level.value,
        "intent_score": lead.intent_score,
        "ai_confidence": lead.ai_confidence,
        "ai_summary": lead.ai_summary,
        "ai_suggestion": lead.ai_suggestion,
        "needs": lead.needs or [],
        "tags": lead.tags or [],
        "last_contact_at": lead.last_contact_at.isoformat() if lead.last_contact_at else None,
        "contact_count": lead.contact_count,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat()
    }


@router.post("")
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建线索"""
    lead = Lead(
        name=lead_data.name,
        company=lead_data.company,
        phone=lead_data.phone,
        email=lead_data.email,
        wechat=lead_data.wechat,
        source=lead_data.source,
        source_url=lead_data.source_url,
        source_content=lead_data.source_content,
        needs=lead_data.needs,
        tags=lead_data.tags
    )
    
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    
    logger.info(f"创建线索: {lead.name} from {lead.source.value}")
    
    return {
        "id": str(lead.id),
        "message": "线索创建成功"
    }


@router.patch("/{lead_id}")
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新线索"""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    
    # 更新字段
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(lead, field, value)
    
    await db.commit()
    
    return {"message": "线索更新成功"}


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """删除线索"""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    
    await db.delete(lead)
    await db.commit()
    
    return {"message": "线索已删除"}


@router.post("/{lead_id}/convert")
async def convert_lead_to_customer(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """将线索转化为客户"""
    from app.models import Customer, IntentLevel, CustomerSource
    
    # 获取线索
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    
    if lead.status == LeadStatus.CONVERTED:
        raise HTTPException(status_code=400, detail="该线索已转化为客户")
    
    # 映射意向等级
    intent_level_map = {
        LeadIntentLevel.HIGH: IntentLevel.A,
        LeadIntentLevel.MEDIUM: IntentLevel.B,
        LeadIntentLevel.LOW: IntentLevel.C,
        LeadIntentLevel.UNKNOWN: IntentLevel.C,
    }
    
    # 映射来源 - 线索来源 -> 客户来源
    # CustomerSource 只有: WECHAT, WEBSITE, REFERRAL, AD, OTHER
    source_map = {
        LeadSource.GOOGLE: CustomerSource.WEBSITE,
        LeadSource.WEIBO: CustomerSource.OTHER,
        LeadSource.ZHIHU: CustomerSource.OTHER,
        LeadSource.TIEBA: CustomerSource.OTHER,
        LeadSource.WECHAT: CustomerSource.WECHAT,
        LeadSource.YOUTUBE: CustomerSource.OTHER,
        LeadSource.FACEBOOK: CustomerSource.AD,
        LeadSource.LINKEDIN: CustomerSource.OTHER,
        LeadSource.B2B_ALIBABA: CustomerSource.OTHER,
        LeadSource.B2B_1688: CustomerSource.OTHER,
        LeadSource.MANUAL: CustomerSource.OTHER,
        LeadSource.OTHER: CustomerSource.OTHER,
    }
    
    # 创建客户
    customer = Customer(
        name=lead.name or "未知客户",
        company=lead.company,
        phone=lead.phone,
        email=lead.email,
        wechat_id=lead.wechat,
        source=source_map.get(lead.source, CustomerSource.OTHER),
        source_detail=f"来自线索: {lead.id}, 需求: {lead.needs}",
        intent_level=intent_level_map.get(lead.intent_level, IntentLevel.C),
        intent_score=lead.intent_score,
        tags=lead.tags or [],
        cargo_types=lead.needs or [],
        last_contact_at=datetime.utcnow(),  # 标记为首次联系时间
        follow_count=0  # 初始跟进次数
    )
    
    db.add(customer)
    
    # 更新线索状态
    lead.status = LeadStatus.CONVERTED
    
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"线索 {lead.name} 转化为客户 {customer.id}")
    
    # ==================== 自动触发首次跟进 ====================
    try:
        from app.agents.follow_agent import follow_agent
        from app.services.notification import notification_service
        from sqlalchemy import text
        
        # 1. 生成首次跟进内容
        follow_result = await follow_agent.process({
            "customer_info": {
                "name": customer.name,
                "company": customer.company,
                "source": lead.source.value if lead.source else "unknown"
            },
            "intent_level": customer.intent_level.value if customer.intent_level else "B",
            "last_contact": "首次联系",
            "last_conversation": f"线索来源: {lead.ai_summary or '无'}",
            "purpose": "首次跟进 - 新线索转化"
        })
        
        follow_message = follow_result.get("follow_message", "")
        next_follow_time = follow_result.get("next_follow_time")
        
        # 2. 创建首次跟进记录
        if follow_message:
            await db.execute(
                text("""
                    INSERT INTO follow_records 
                    (customer_id, follow_type, channel, executor_type, executor_name, 
                     content, intent_before, intent_after, created_at)
                    VALUES (:customer_id, 'first_contact', 'system', 'follow', '小跟',
                            :content, :intent_score, :intent_score, NOW())
                """),
                {
                    "customer_id": str(customer.id),
                    "content": f"[自动生成首次跟进]\n{follow_message}",
                    "intent_score": customer.intent_score or 0
                }
            )
            await db.commit()
        
        # 3. 更新客户下次跟进时间
        if next_follow_time:
            from datetime import datetime as dt
            # 将字符串转换为 datetime 对象
            if isinstance(next_follow_time, str):
                try:
                    next_follow_dt = dt.fromisoformat(next_follow_time.replace('Z', '+00:00'))
                except:
                    next_follow_dt = dt.now()
            else:
                next_follow_dt = next_follow_time
            
            await db.execute(
                text("""
                    UPDATE customers 
                    SET next_follow_at = :next_follow_time
                    WHERE id = :customer_id
                """),
                {
                    "customer_id": str(customer.id),
                    "next_follow_time": next_follow_dt
                }
            )
            await db.commit()
        
        # 4. 发送通知
        await notification_service.create_notification(
            title="🎯 新客户待跟进",
            content=f"线索「{lead.name}」已转化为客户，小跟已生成首次跟进话术，请及时联系！",
            notification_type="follow_reminder",
            priority="high" if customer.intent_level and customer.intent_level.value == "A" else "medium",
            related_id=str(customer.id),
            related_type="customer"
        )
        
        logger.info(f"✅ 已为新客户 {customer.name} 触发首次跟进流程")
        
    except Exception as e:
        # 跟进触发失败不影响转化结果
        logger.error(f"触发首次跟进失败: {e}")
    
    return {
        "message": "转化成功",
        "customer_id": str(customer.id),
        "lead_id": str(lead.id)
    }


@router.post("/{lead_id}/contact")
async def contact_lead(
    lead_id: UUID,
    message: str = "",
    db: AsyncSession = Depends(get_db)
):
    """联系线索"""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    
    # 更新线索状态和联系记录
    if lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.CONTACTED
    
    lead.last_contact_at = datetime.utcnow()
    lead.contact_count = (lead.contact_count or 0) + 1
    
    await db.commit()
    
    logger.info(f"联系线索: {lead.name}, 第{lead.contact_count}次")
    
    return {
        "message": "联系记录已更新",
        "lead_id": str(lead.id),
        "contact_count": lead.contact_count
    }


@router.post("/{lead_id}/filter")
async def filter_lead(
    lead_id: UUID,
    reason: str = "",
    db: AsyncSession = Depends(get_db)
):
    """过滤/排除线索 - 将不合适的线索标记为无效"""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    
    if lead.status == LeadStatus.CONVERTED:
        raise HTTPException(status_code=400, detail="该线索已转化为客户，无法过滤")
    
    if lead.status == LeadStatus.INVALID:
        raise HTTPException(status_code=400, detail="该线索已被过滤")
    
    # 更新线索状态为无效
    lead.status = LeadStatus.INVALID
    
    # 如果提供了原因，记录到extra_data
    if reason:
        extra_data = lead.extra_data or {}
        extra_data["filter_reason"] = reason
        extra_data["filtered_at"] = datetime.utcnow().isoformat()
        lead.extra_data = extra_data
    
    await db.commit()
    
    logger.info(f"过滤线索: {lead.name or lead.id}, 原因: {reason or '无'}")
    
    return {
        "message": "线索已过滤",
        "lead_id": str(lead.id)
    }


@router.post("/{lead_id}/restore")
async def restore_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """恢复被过滤的线索"""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="线索不存在")
    
    if lead.status != LeadStatus.INVALID:
        raise HTTPException(status_code=400, detail="该线索未被过滤，无需恢复")
    
    # 恢复线索状态为新线索
    lead.status = LeadStatus.NEW
    
    # 清除过滤记录
    if lead.extra_data:
        extra_data = lead.extra_data.copy()
        extra_data.pop("filter_reason", None)
        extra_data.pop("filtered_at", None)
        lead.extra_data = extra_data
    
    await db.commit()
    
    logger.info(f"恢复线索: {lead.name or lead.id}")
    
    return {
        "message": "线索已恢复",
        "lead_id": str(lead.id)
    }


@router.post("/hunt")
async def start_lead_hunting(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    启动线索狩猎任务
    在后台运行，搜索互联网上的潜在客户
    """
    from app.agents.lead_hunter import LeadHunterAgent
    from app.core.config import settings
    
    # 检查API配置
    if not getattr(settings, 'SERPER_API_KEY', None):
        raise HTTPException(
            status_code=400,
            detail="搜索API未配置。请在系统设置中配置 SERPER_API_KEY 以启用线索搜索功能。您可以在 https://serper.dev 注册获取API密钥。"
        )
    
    async def hunt_leads():
        try:
            # 创建新的数据库会话
            from app.models import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                hunter = LeadHunterAgent()
                results = await hunter.process({"action": "hunt"})
                
                # 检查是否有错误
                if results.get("error"):
                    logger.error(f"线索狩猎失败: {results.get('error')}")
                    return
                
                # 保存找到的线索
                leads_saved = 0
                for lead_data in results.get("leads_found", []):
                    try:
                        # 映射source到LeadSource枚举
                        source_str = lead_data.get("source", "other")
                        source_map = {
                            "google": LeadSource.GOOGLE,
                            "weibo": LeadSource.WEIBO,
                            "zhihu": LeadSource.ZHIHU,
                            "tieba": LeadSource.TIEBA,
                            "wechat": LeadSource.WECHAT,
                            "manual": LeadSource.MANUAL,
                        }
                        source = source_map.get(source_str, LeadSource.OTHER)
                        
                        # 映射intent_level
                        intent_str = lead_data.get("intent_level", "unknown")
                        intent_map = {
                            "high": LeadIntentLevel.HIGH,
                            "medium": LeadIntentLevel.MEDIUM,
                            "low": LeadIntentLevel.LOW,
                        }
                        intent_level = intent_map.get(intent_str, LeadIntentLevel.UNKNOWN)
                        
                        # 获取联系信息
                        contact_info = lead_data.get("contact_info", {})
                        
                        lead = Lead(
                            name=contact_info.get("name") or lead_data.get("title", "")[:50],
                            company=contact_info.get("company"),
                            phone=contact_info.get("phone"),
                            email=contact_info.get("email"),
                            wechat=contact_info.get("wechat"),
                            source=source,
                            source_url=lead_data.get("url"),
                            source_content=lead_data.get("content", "")[:2000],  # 限制长度
                            intent_level=intent_level,
                            ai_confidence=lead_data.get("confidence", 0),
                            ai_summary=lead_data.get("summary"),
                            ai_suggestion=lead_data.get("follow_up_suggestion"),
                            needs=lead_data.get("needs", [])
                        )
                        session.add(lead)
                        leads_saved += 1
                    except Exception as e:
                        logger.error(f"保存线索失败: {e}")
                        continue
                
                await session.commit()
                logger.info(f"线索狩猎完成，找到 {results.get('total_leads', 0)} 条线索，成功保存 {leads_saved} 条")
                
        except Exception as e:
            logger.error(f"线索狩猎失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    background_tasks.add_task(hunt_leads)
    
    return {
        "message": "线索狩猎任务已启动",
        "status": "running"
    }
