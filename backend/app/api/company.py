"""
公司配置API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Any
import logging

from ..models.database import get_db
from ..models.company_config import CompanyConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/company", tags=["company"])


class RouteItem(BaseModel):
    from_location: str
    to_location: str
    transport: str  # 海运/空运/铁路
    time: str
    price_ref: Optional[str] = None


class ProductItem(BaseModel):
    name: str
    description: Optional[str] = None
    features: Optional[List[str]] = []


class FAQItem(BaseModel):
    question: str
    answer: str


class CompanyConfigUpdate(BaseModel):
    company_name: Optional[str] = None
    company_intro: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    contact_wechat: Optional[str] = None
    address: Optional[str] = None
    products: Optional[List[dict]] = None
    service_routes: Optional[List[dict]] = None
    advantages: Optional[List[str]] = None
    faq: Optional[List[dict]] = None
    price_policy: Optional[str] = None
    # 新增字段
    logo_url: Optional[str] = None
    focus_markets: Optional[List[str]] = None
    company_website: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[str] = None
    business_scope: Optional[str] = None
    social_media: Optional[dict] = None
    brand_slogan: Optional[str] = None
    brand_colors: Optional[dict] = None
    company_values: Optional[List[str]] = None
    content_tone: Optional[str] = None
    content_focus_keywords: Optional[List[str]] = None
    forbidden_content: Optional[List[str]] = None
    # 品牌资产
    brand_assets: Optional[dict] = None


class CompanyConfigResponse(BaseModel):
    id: str
    company_name: str
    company_intro: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    contact_wechat: Optional[str]
    address: Optional[str]
    products: List[Any]
    service_routes: List[Any]
    advantages: List[str]
    faq: List[Any]
    price_policy: Optional[str]


@router.get("/config")
async def get_company_config(db: AsyncSession = Depends(get_db)):
    """获取公司配置"""
    try:
        result = await db.execute(select(CompanyConfig).limit(1))
        config = result.scalar_one_or_none()
        
        if not config:
            # 如果没有配置，创建默认配置
            config = CompanyConfig(
                company_name="我的物流公司",
                company_intro="专业的国际物流服务商",
                products=[
                    {"name": "海运整柜", "description": "FCL整箱海运服务", "features": ["价格实惠", "适合大货量"]},
                    {"name": "海运拼箱", "description": "LCL拼箱海运服务", "features": ["灵活方便", "适合小货量"]},
                    {"name": "空运快递", "description": "国际空运服务", "features": ["时效快", "适合紧急货物"]},
                ],
                service_routes=[
                    {"from_location": "中国", "to_location": "美国", "transport": "海运", "time": "25-30天", "price_ref": ""},
                    {"from_location": "中国", "to_location": "欧洲", "transport": "海运", "time": "30-35天", "price_ref": ""},
                    {"from_location": "中国", "to_location": "东南亚", "transport": "海运", "time": "7-12天", "price_ref": ""},
                ],
                advantages=["价格优惠", "时效保障", "专业服务", "一对一客服"],
                faq=[
                    {"question": "如何查询运费?", "answer": "请提供货物品类、重量/体积、起运地和目的地，我们会为您报价。"},
                    {"question": "运输时效是多少?", "answer": "根据不同航线和运输方式，时效有所不同，详情可咨询客服。"},
                ],
                price_policy="根据货物类型、航线、时效等因素综合报价，量大从优。"
            )
            db.add(config)
            await db.commit()
            await db.refresh(config)
        
        # 获取新字段（使用getattr防止字段不存在时报错）
        return {
            "id": str(config.id),
            "company_name": config.company_name or "",
            "company_intro": config.company_intro,
            "contact_phone": config.contact_phone,
            "contact_email": config.contact_email,
            "contact_wechat": config.contact_wechat,
            "address": config.address,
            "products": config.products or [],
            "service_routes": config.service_routes or [],
            "advantages": config.advantages or [],
            "faq": config.faq or [],
            "price_policy": config.price_policy,
            # 新增字段
            "logo_url": getattr(config, 'logo_url', None),
            "focus_markets": getattr(config, 'focus_markets', None) or [],
            "company_website": getattr(config, 'company_website', None),
            "founded_year": getattr(config, 'founded_year', None),
            "employee_count": getattr(config, 'employee_count', None),
            "business_scope": getattr(config, 'business_scope', None),
            "social_media": getattr(config, 'social_media', None) or {},
            "brand_slogan": getattr(config, 'brand_slogan', None),
            "brand_colors": getattr(config, 'brand_colors', None) or {},
            "company_values": getattr(config, 'company_values', None) or [],
            "content_tone": getattr(config, 'content_tone', None) or 'professional',
            "content_focus_keywords": getattr(config, 'content_focus_keywords', None) or [],
            "forbidden_content": getattr(config, 'forbidden_content', None) or [],
            # 品牌资产
            "brand_assets": getattr(config, 'brand_assets', None) or {}
        }
    except Exception as e:
        logger.error(f"获取公司配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_company_config(
    data: CompanyConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新公司配置"""
    try:
        result = await db.execute(select(CompanyConfig).limit(1))
        config = result.scalar_one_or_none()
        
        if not config:
            config = CompanyConfig()
            db.add(config)
        
        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(config, key, value)
        
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"公司配置已更新")
        
        return {
            "success": True,
            "message": "公司配置已更新",
            "id": str(config.id)
        }
    except Exception as e:
        logger.error(f"更新公司配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-context")
async def get_prompt_context(db: AsyncSession = Depends(get_db)):
    """
    获取用于AI提示词的公司上下文信息
    这个接口会被AI员工调用，获取公司信息用于生成回复
    """
    try:
        result = await db.execute(select(CompanyConfig).limit(1))
        config = result.scalar_one_or_none()
        
        if not config:
            return {"context": ""}
        
        # 构建上下文文本
        lines = []
        
        if config.company_name:
            lines.append(f"公司名称：{config.company_name}")
        
        if config.company_intro:
            lines.append(f"公司简介：{config.company_intro}")
        
        if config.products:
            products_text = []
            for p in config.products:
                name = p.get('name', '')
                desc = p.get('description', '')
                features = p.get('features', [])
                products_text.append(f"- {name}: {desc} (特点: {', '.join(features)})")
            if products_text:
                lines.append("产品服务：")
                lines.extend(products_text)
        
        if config.service_routes:
            routes_text = []
            for r in config.service_routes:
                from_loc = r.get('from_location', '')
                to_loc = r.get('to_location', '')
                transport = r.get('transport', '')
                time = r.get('time', '')
                price_ref = r.get('price_ref', '')
                route_info = f"- {from_loc}→{to_loc} ({transport}): {time}"
                if price_ref:
                    route_info += f", 参考价格: {price_ref}"
                routes_text.append(route_info)
            if routes_text:
                lines.append("服务航线：")
                lines.extend(routes_text)
        
        if config.advantages:
            lines.append(f"公司优势：{', '.join(config.advantages)}")
        
        if config.price_policy:
            lines.append(f"价格政策：{config.price_policy}")
        
        if config.contact_phone:
            lines.append(f"联系电话：{config.contact_phone}")
        
        if config.contact_wechat:
            lines.append(f"客服微信：{config.contact_wechat}")
        
        return {
            "context": "\n".join(lines),
            "company_name": config.company_name or "",
            "faq": config.faq or []
        }
    except Exception as e:
        logger.error(f"获取提示词上下文失败: {e}")
        return {"context": "", "company_name": "", "faq": []}
