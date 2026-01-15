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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取线索列表"""
    query = select(Lead)
    
    # 过滤条件
    if status:
        query = query.where(Lead.status == status)
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
    
    # 按状态统计
    status_stats = {}
    for status in LeadStatus:
        result = await db.execute(
            select(func.count(Lead.id)).where(Lead.status == status)
        )
        status_stats[status.value] = result.scalar()
    
    # 按意向等级统计
    intent_stats = {}
    for level in LeadIntentLevel:
        result = await db.execute(
            select(func.count(Lead.id)).where(Lead.intent_level == level)
        )
        intent_stats[level.value] = result.scalar()
    
    # 按来源统计
    source_stats = {}
    for src in LeadSource:
        result = await db.execute(
            select(func.count(Lead.id)).where(Lead.source == src)
        )
        count = result.scalar()
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
    
    # 映射来源
    source_map = {
        LeadSource.GOOGLE: CustomerSource.WECHAT,
        LeadSource.WEIBO: CustomerSource.WECHAT,
        LeadSource.ZHIHU: CustomerSource.WECHAT,
        LeadSource.TIEBA: CustomerSource.WECHAT,
        LeadSource.WECHAT: CustomerSource.WECHAT,
        LeadSource.MANUAL: CustomerSource.MANUAL,
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
        intent_level=intent_level_map.get(lead.intent_level, IntentLevel.C),
        intent_score=lead.intent_score,
        tags=lead.tags or [],
        profile={"from_lead": str(lead.id), "needs": lead.needs}
    )
    
    db.add(customer)
    
    # 更新线索状态
    lead.status = LeadStatus.CONVERTED
    
    await db.commit()
    await db.refresh(customer)
    
    logger.info(f"线索 {lead.name} 转化为客户 {customer.id}")
    
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
    
    async def hunt_leads():
        try:
            hunter = LeadHunterAgent()
            results = await hunter.process({"action": "hunt"})
            
            # 保存找到的线索
            for lead_data in results.get("leads_found", []):
                lead = Lead(
                    name=lead_data.get("contact_info", {}).get("name"),
                    company=lead_data.get("contact_info", {}).get("company"),
                    phone=lead_data.get("contact_info", {}).get("phone"),
                    email=lead_data.get("contact_info", {}).get("email"),
                    wechat=lead_data.get("contact_info", {}).get("wechat"),
                    source=LeadSource(lead_data.get("source", "other")),
                    source_url=lead_data.get("url"),
                    source_content=lead_data.get("content"),
                    intent_level=LeadIntentLevel(lead_data.get("intent_level", "unknown")),
                    ai_confidence=lead_data.get("confidence", 0),
                    ai_summary=lead_data.get("summary"),
                    ai_suggestion=lead_data.get("follow_up_suggestion"),
                    needs=lead_data.get("needs", [])
                )
                db.add(lead)
            
            await db.commit()
            logger.info(f"线索狩猎完成，找到 {results.get('total_leads', 0)} 条线索")
            
        except Exception as e:
            logger.error(f"线索狩猎失败: {e}")
    
    background_tasks.add_task(hunt_leads)
    
    return {
        "message": "线索狩猎任务已启动",
        "status": "running"
    }
