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
    
    # ============ 新增字段 ============
    
    # Logo和品牌（使用Text类型支持base64存储）
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand_slogan: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 品牌口号
    brand_colors: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)  # 品牌色 {"primary": "#xxx", "secondary": "#xxx"}
    company_values: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # 企业价值观
    
    # 聚焦市场和业务范围
    focus_markets: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # 聚焦市场/服务区域
    business_scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 业务范围描述
    
    # 公司详情
    company_website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 成立年份
    employee_count: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 员工规模
    
    # 社交媒体账号
    # 格式: {"wechat_official": "公众号ID", "douyin": "抖音号", "xiaohongshu": "小红书号", "video_account": "视频号"}
    social_media: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    
    # 内容生成相关配置
    content_tone: Mapped[Optional[str]] = mapped_column(String(50), default='professional')  # 内容风格
    content_focus_keywords: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # 内容关键词
    forbidden_content: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # 禁止出现的内容
    
    # ============ 品牌资产 ============
    # 格式: {
    #   "logo": {"main": "...", "white": "...", "icon": "..."},
    #   "qrcode": {"wechat": "...", "wechat_official": "...", "douyin": "...", "xiaohongshu": "..."},
    #   "watermark": {"enabled": true, "position": "bottom-right", "opacity": 0.8, "image": "..."},
    #   "video_assets": {"intro_video": "...", "outro_template": "..."}
    # }
    brand_assets: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    
    # ============ 时间戳 ============
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())
