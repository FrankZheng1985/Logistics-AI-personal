"""
对话记录数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.models.database import Base


class AgentType(str, enum.Enum):
    """AI员工类型"""
    COORDINATOR = "coordinator"   # 小调 - 调度主管
    VIDEO_CREATOR = "video_creator"  # 小视 - 视频创作
    COPYWRITER = "copywriter"     # 小文 - 文案策划
    SALES = "sales"               # 小销 - 销售客服
    FOLLOW = "follow"             # 小跟 - 跟进专员
    ANALYST = "analyst"           # 小析 - 客户分析
    LEAD_HUNTER = "lead_hunter"   # 小猎 - 线索猎手
    ANALYST2 = "analyst2"         # 小析2 - 群聊情报员


class MessageType(str, enum.Enum):
    """消息类型"""
    INBOUND = "inbound"    # 客户发来的消息
    OUTBOUND = "outbound"  # AI发出的消息


class Conversation(Base):
    """对话记录表"""
    __tablename__ = "conversations"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # 关联客户
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 对话信息
    session_id: Mapped[Optional[str]] = mapped_column(String(100))
    agent_type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name='agent_type', create_type=False, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, name='message_type', create_type=False, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 意向分析
    intent_delta: Mapped[int] = mapped_column(Integer, default=0)
    intent_signals: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    
    # 额外数据
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow
    )
    
    # 关系
    customer = relationship("Customer", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation {self.agent_type.value} -> {self.message_type.value}>"
