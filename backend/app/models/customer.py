"""
客户数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Enum, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.models.database import Base


class IntentLevel(str, enum.Enum):
    """客户意向等级"""
    S = "S"  # 高意向 80+
    A = "A"  # 较高意向 60-79
    B = "B"  # 中等意向 30-59
    C = "C"  # 低意向 <30


class CustomerSource(str, enum.Enum):
    """客户来源"""
    WECHAT = "wechat"
    WEBSITE = "website"
    REFERRAL = "referral"
    AD = "ad"
    OTHER = "other"
    
    @classmethod
    def _missing_(cls, value):
        """处理数据库返回的值"""
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        return None


class Customer(Base):
    """客户表"""
    __tablename__ = "customers"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # 基本信息
    name: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    wechat_id: Mapped[Optional[str]] = mapped_column(String(100))
    wechat_open_id: Mapped[Optional[str]] = mapped_column(String(100))
    company: Mapped[Optional[str]] = mapped_column(String(200))
    
    # 来源追踪
    source: Mapped[CustomerSource] = mapped_column(
        Enum(
            CustomerSource, 
            name='customer_source', 
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ), 
        default=CustomerSource.OTHER
    )
    source_detail: Mapped[Optional[str]] = mapped_column(String(200))
    
    # 意向评估
    intent_score: Mapped[int] = mapped_column(Integer, default=0)
    intent_level: Mapped[IntentLevel] = mapped_column(
        Enum(IntentLevel, name='intent_level', create_type=False), 
        default=IntentLevel.C
    )
    tags: Mapped[List[str]] = mapped_column(ARRAY(String(50)), default=[])
    
    # 业务信息
    cargo_types: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))
    routes: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(100)))
    estimated_volume: Mapped[Optional[str]] = mapped_column(String(50))
    
    # 跟进状态
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id")
    )
    last_contact_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_follow_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    follow_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
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
    
    # 关系
    conversations = relationship("Conversation", back_populates="customer")
    tasks = relationship("AITask", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer {self.name} ({self.intent_level.value})>"
    
    def update_intent_level(self):
        """根据分数更新意向等级"""
        if self.intent_score >= 80:
            self.intent_level = IntentLevel.S
        elif self.intent_score >= 60:
            self.intent_level = IntentLevel.A
        elif self.intent_score >= 30:
            self.intent_level = IntentLevel.B
        else:
            self.intent_level = IntentLevel.C
