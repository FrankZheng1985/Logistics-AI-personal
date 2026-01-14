"""
渠道配置模型
支持多渠道消息接入：企业微信、网站、抖音、小红书等
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.models.database import Base


class ChannelType(str, enum.Enum):
    """渠道类型"""
    WECHAT_WORK = "wechat_work"      # 企业微信
    WECHAT_MP = "wechat_mp"          # 微信公众号
    WEBSITE = "website"              # 网站在线客服
    DOUYIN = "douyin"                # 抖音私信
    XIAOHONGSHU = "xiaohongshu"      # 小红书
    PHONE = "phone"                  # 电话
    EMAIL = "email"                  # 邮件
    OTHER = "other"                  # 其他


class ChannelConfig(Base):
    """渠道配置表"""
    __tablename__ = "channel_configs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 渠道名称
    channel_type: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, name='channel_type', create_type=False),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # 配置参数 (JSON格式存储各渠道特有配置)
    # 例如：企业微信需要 corp_id, agent_id, secret 等
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # 状态
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 统计
    total_messages: Mapped[int] = mapped_column(default=0)
    today_messages: Mapped[int] = mapped_column(default=0)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    def __repr__(self):
        return f"<ChannelConfig {self.name} ({self.channel_type.value})>"
