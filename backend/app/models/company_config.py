"""
公司配置模型 - 存储公司产品、服务、区域等信息
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, TIMESTAMP, Integer, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


class CompanyConfig(Base):
    """公司配置表"""
    __tablename__ = "company_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 公司基本信息
    company_name: Mapped[str] = mapped_column(String(200), default="")
    company_intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_wechat: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # 产品与服务 (JSON格式存储)
    # 格式: [{"name": "海运整柜", "description": "...", "features": ["..."]}]
    products: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    
    # 服务区域/航线
    # 格式: [{"from": "中国", "to": "美国", "time": "25-30天", "price_ref": "...", "transport": "海运"}]
    service_routes: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    
    # 公司优势
    # 格式: ["价格优惠", "时效快", "服务好"]
    advantages: Mapped[Optional[list]] = mapped_column(ARRAY(String), default=list)
    
    # 常见FAQ
    # 格式: [{"question": "...", "answer": "..."}]
    faq: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    
    # 价格参考说明
    price_policy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())
