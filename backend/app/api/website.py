"""
WordPress网站对接API端点

提供以下功能:
- 货物追踪查询
- 报价请求提交
- 服务信息获取
- 客户数据同步
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.database import get_db
from app.models.lead import Lead
from app.models.customer import Customer


router = APIRouter(prefix="/website", tags=["网站对接"])


# ==================== 数据模型 ====================

class TrackingRequest(BaseModel):
    """追踪请求"""
    tracking_number: str = Field(..., min_length=1, max_length=100, description="追踪号码")


class TrackingEvent(BaseModel):
    """追踪事件"""
    time: str
    status: str
    location: str


class TrackingResponse(BaseModel):
    """追踪响应"""
    tracking_number: str
    status: str
    status_text: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    estimated_delivery: Optional[str] = None
    timeline: List[TrackingEvent] = []


class QuoteRequest(BaseModel):
    """报价请求"""
    source: str = "website_quote"
    name: str = Field(..., min_length=1, max_length=100, description="联系人姓名")
    email: EmailStr = Field(..., description="电子邮箱")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    company: Optional[str] = Field(None, max_length=200, description="公司名称")
    content: Optional[str] = Field(None, description="请求内容")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="额外数据")


class QuoteResponse(BaseModel):
    """报价响应"""
    id: int
    message: str


class ServiceInfo(BaseModel):
    """服务信息"""
    id: str
    name: str
    description: str
    icon: str
    features: List[str]


class ContactRequest(BaseModel):
    """联系请求"""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)


# ==================== API端点 ====================

@router.post("/tracking", response_model=TrackingResponse, summary="货物追踪查询")
async def track_shipment(
    request: TrackingRequest,
    client_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    查询货物追踪信息
    
    根据追踪号码查询货物的当前状态和运输轨迹
    """
    tracking_number = request.tracking_number.strip().upper()
    
    logger.info(f"[Website] 追踪查询: {tracking_number}, IP: {client_request.client.host}")
    
    # 这里应该对接实际的ERP/物流系统
    # 目前返回模拟数据用于测试
    
    # 模拟不同追踪号的不同状态
    import hashlib
    hash_val = int(hashlib.md5(tracking_number.encode()).hexdigest(), 16) % 3
    
    statuses = ['pending', 'in_transit', 'delivered']
    status_texts = {'pending': '处理中', 'in_transit': '运输中', 'delivered': '已签收'}
    
    status = statuses[hash_val]
    
    # 生成模拟时间线
    timeline = []
    base_time = datetime.now()
    
    events = [
        {"status": "快件已揽收", "location": "深圳分拨中心"},
        {"status": "离开深圳分拨中心，发往香港", "location": "深圳分拨中心"},
        {"status": "到达香港国际机场", "location": "香港"},
        {"status": "航班起飞", "location": "香港国际机场"},
        {"status": "到达目的地机场", "location": "洛杉矶国际机场"},
        {"status": "清关中", "location": "美国海关"},
        {"status": "清关完成，正在派送", "location": "洛杉矶配送中心"},
    ]
    
    if status == 'delivered':
        events.append({"status": "已签收", "location": "目的地"})
    
    # 根据状态决定显示多少事件
    event_count = 2 if status == 'pending' else (5 if status == 'in_transit' else len(events))
    
    for i in range(min(event_count, len(events))):
        event_time = base_time.replace(
            hour=max(0, base_time.hour - (event_count - i) * 6),
            minute=0,
            second=0
        )
        timeline.append(TrackingEvent(
            time=event_time.strftime("%Y-%m-%d %H:%M:%S"),
            status=events[i]["status"],
            location=events[i]["location"]
        ))
    
    # 时间倒序
    timeline.reverse()
    
    return TrackingResponse(
        tracking_number=tracking_number,
        status=status,
        status_text=status_texts[status],
        origin="深圳, 中国",
        destination="洛杉矶, 美国",
        estimated_delivery=(base_time.replace(day=base_time.day + 2)).strftime("%Y-%m-%d") if status != 'delivered' else None,
        timeline=timeline
    )


@router.post("/quote-request", response_model=QuoteResponse, summary="提交报价请求")
async def submit_quote_request(
    request: QuoteRequest,
    client_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    提交报价请求
    
    将报价请求保存为线索，供销售团队跟进
    """
    logger.info(f"[Website] 新报价请求: {request.name} <{request.email}>, IP: {client_request.client.host}")
    
    try:
        # 构建线索内容
        content = request.content or ""
        if request.extra_data:
            extra = request.extra_data
            content_parts = ["报价请求详情:"]
            if extra.get('origin'):
                content_parts.append(f"起运地: {extra['origin']}")
            if extra.get('destination'):
                content_parts.append(f"目的地: {extra['destination']}")
            if extra.get('service_type'):
                service_types = {
                    'sea_freight': '海运服务',
                    'air_freight': '空运服务',
                    'land_transport': '陆运服务',
                    'express': '国际快递',
                    'multimodal': '多式联运'
                }
                content_parts.append(f"服务类型: {service_types.get(extra['service_type'], extra['service_type'])}")
            if extra.get('cargo_type'):
                cargo_types = {
                    'general': '普通货物',
                    'dangerous': '危险品',
                    'temperature': '温控货物',
                    'oversized': '超大件',
                    'fragile': '易碎品'
                }
                content_parts.append(f"货物类型: {cargo_types.get(extra['cargo_type'], extra['cargo_type'])}")
            if extra.get('weight'):
                content_parts.append(f"重量: {extra['weight']} KG")
            if extra.get('dimensions'):
                content_parts.append(f"尺寸: {extra['dimensions']}")
            if extra.get('quantity'):
                content_parts.append(f"数量: {extra['quantity']} 件")
            if extra.get('ship_date'):
                content_parts.append(f"预计发货: {extra['ship_date']}")
            
            content = "\n".join(content_parts)
        
        # 创建线索
        lead = Lead(
            source="website",
            source_url=str(client_request.url),
            company_name=request.company,
            contact_name=request.name,
            email=request.email,
            phone=request.phone,
            content=content,
            extra_data=request.extra_data,
            status="new",
            priority=2,  # 网站报价请求优先级较高
            created_at=datetime.utcnow()
        )
        
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        logger.info(f"[Website] 报价请求已保存为线索 ID: {lead.id}")
        
        # 触发通知（可选）
        try:
            from app.services.notification_service import notification_service
            await notification_service.send_notification(
                title="新网站报价请求",
                content=f"客户 {request.name} 提交了报价请求\n路线: {request.extra_data.get('origin', '未知')} → {request.extra_data.get('destination', '未知')}" if request.extra_data else f"客户 {request.name} 提交了报价请求",
                notification_type="lead",
                data={"lead_id": lead.id}
            )
        except Exception as e:
            logger.warning(f"发送通知失败: {e}")
        
        return QuoteResponse(
            id=lead.id,
            message="报价请求已提交，我们将在1个工作日内与您联系"
        )
        
    except Exception as e:
        logger.error(f"[Website] 保存报价请求失败: {e}")
        raise HTTPException(status_code=500, detail="提交失败，请稍后重试")


@router.get("/services", response_model=List[ServiceInfo], summary="获取服务列表")
async def get_services():
    """
    获取公司服务列表
    
    返回所有可用的物流服务信息
    """
    services = [
        ServiceInfo(
            id="sea_freight",
            name="海运服务",
            description="提供整箱(FCL)和拼箱(LCL)海运服务，覆盖全球主要港口",
            icon="ship",
            features=["整箱/拼箱运输", "全球主要港口覆盖", "门到门服务", "特种柜运输"]
        ),
        ServiceInfo(
            id="air_freight",
            name="空运服务",
            description="快速、可靠的国际空运服务，满足您对时效的严格要求",
            icon="plane",
            features=["特快/标准空运", "机场到机场/门到门", "包机服务", "危险品空运"]
        ),
        ServiceInfo(
            id="land_transport",
            name="陆运服务",
            description="专业的公路和铁路运输服务，覆盖中国全境及中欧班列沿线国家",
            icon="truck",
            features=["整车/零担运输", "中欧铁路班列", "跨境公路运输", "国内配送网络"]
        ),
        ServiceInfo(
            id="warehousing",
            name="仓储服务",
            description="现代化仓储设施，智能化库存管理系统",
            icon="warehouse",
            features=["保税仓储", "海外仓服务", "库存管理", "增值服务"]
        ),
        ServiceInfo(
            id="customs",
            name="报关清关",
            description="专业的报关团队，熟悉各国海关政策法规",
            icon="file-alt",
            features=["进出口报关", "商检代理", "单证服务", "关税筹划"]
        ),
        ServiceInfo(
            id="express",
            name="国际快递",
            description="快速安全的国际快递服务，适合小件商品和文件寄送",
            icon="box",
            features=["文件快递", "包裹快递", "全程追踪", "签收确认"]
        ),
    ]
    
    return services


@router.post("/contact", summary="提交联系消息")
async def submit_contact(
    request: ContactRequest,
    client_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    提交联系消息
    
    用户通过网站联系表单提交的消息
    """
    logger.info(f"[Website] 新联系消息: {request.name} <{request.email}>, 主题: {request.subject}")
    
    try:
        # 创建线索（标记为联系消息）
        lead = Lead(
            source="website_contact",
            source_url=str(client_request.url),
            contact_name=request.name,
            email=request.email,
            phone=request.phone,
            content=f"【{request.subject}】\n\n{request.message}",
            status="new",
            priority=1,
            created_at=datetime.utcnow()
        )
        
        db.add(lead)
        await db.commit()
        
        return {"success": True, "message": "消息已发送，我们会尽快回复您"}
        
    except Exception as e:
        logger.error(f"[Website] 保存联系消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送失败，请稍后重试")


@router.get("/company-info", summary="获取公司信息")
async def get_company_info(db: AsyncSession = Depends(get_db)):
    """
    获取公司基本信息
    
    返回公司名称、联系方式等信息
    """
    try:
        from app.models.company_config import CompanyConfig
        
        result = await db.execute(select(CompanyConfig).limit(1))
        config = result.scalar_one_or_none()
        
        if config:
            return {
                "name": config.name,
                "description": config.description,
                "phone": config.phone,
                "email": config.email,
                "address": config.address,
                "website": config.website,
                "working_hours": "周一至周五 9:00 - 18:00"
            }
        
        # 默认信息
        return {
            "name": "Sysafari Logistics",
            "description": "专业的国际物流服务商",
            "phone": "+86 400-XXX-XXXX",
            "email": "info@sysafari.com",
            "address": "",
            "website": "",
            "working_hours": "周一至周五 9:00 - 18:00"
        }
        
    except Exception as e:
        logger.error(f"获取公司信息失败: {e}")
        return {
            "name": "Sysafari Logistics",
            "description": "专业的国际物流服务商",
            "phone": "+86 400-XXX-XXXX",
            "email": "info@sysafari.com",
            "address": "",
            "website": "",
            "working_hours": "周一至周五 9:00 - 18:00"
        }


@router.post("/webhook", summary="接收WordPress Webhook")
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    接收WordPress发送的Webhook通知
    
    用于处理WordPress端的事件，如用户注册、订单创建等
    """
    try:
        data = await request.json()
        event_type = data.get("event", "")
        
        logger.info(f"[Website Webhook] 收到事件: {event_type}")
        
        if event_type == "user.registered":
            # 处理用户注册
            user_data = data.get("user", {})
            logger.info(f"WordPress用户注册: {user_data.get('email')}")
            
        elif event_type == "quote.submitted":
            # 处理报价提交
            quote_data = data.get("quote", {})
            logger.info(f"WordPress报价提交: {quote_data.get('id')}")
            
        return {"received": True, "event": event_type}
        
    except Exception as e:
        logger.error(f"处理Webhook失败: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook data")


@router.get("/stats", summary="获取网站统计数据")
async def get_website_stats(db: AsyncSession = Depends(get_db)):
    """
    获取网站相关统计数据
    
    返回报价请求数量、线索转化等统计
    """
    from sqlalchemy import func
    
    try:
        # 统计网站来源的线索
        today = datetime.utcnow().date()
        
        # 总报价请求数
        total_quotes = await db.scalar(
            select(func.count(Lead.id)).where(
                or_(Lead.source == "website", Lead.source == "website_quote")
            )
        )
        
        # 今日报价请求数
        today_quotes = await db.scalar(
            select(func.count(Lead.id)).where(
                and_(
                    or_(Lead.source == "website", Lead.source == "website_quote"),
                    func.date(Lead.created_at) == today
                )
            )
        )
        
        # 本周报价请求数
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        week_quotes = await db.scalar(
            select(func.count(Lead.id)).where(
                and_(
                    or_(Lead.source == "website", Lead.source == "website_quote"),
                    func.date(Lead.created_at) >= week_ago
                )
            )
        )
        
        return {
            "total_quotes": total_quotes or 0,
            "today_quotes": today_quotes or 0,
            "week_quotes": week_quotes or 0,
            "conversion_rate": 0  # 需要根据实际业务逻辑计算
        }
        
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return {
            "total_quotes": 0,
            "today_quotes": 0,
            "week_quotes": 0,
            "conversion_rate": 0
        }
