"""
AI员工数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.models.database import Base
from app.models.conversation import AgentType


class AgentStatus(str, enum.Enum):
    """AI员工状态"""
    ONLINE = "online"    # 在线
    BUSY = "busy"        # 忙碌
    OFFLINE = "offline"  # 离线


class AIAgent(Base):
    """AI员工表"""
    __tablename__ = "ai_agents"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # 状态
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), 
        default=AgentStatus.ONLINE
    )
    current_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    
    # 统计
    tasks_completed_today: Mapped[int] = mapped_column(Integer, default=0)
    total_tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    
    # 配置
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    
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
        return f"<AIAgent {self.name} ({self.status.value})>"
    
    def set_busy(self, task_id: uuid.UUID):
        """设置为忙碌状态"""
        self.status = AgentStatus.BUSY
        self.current_task_id = task_id
    
    def set_online(self):
        """设置为在线状态"""
        self.status = AgentStatus.ONLINE
        self.current_task_id = None
    
    def complete_task(self):
        """完成一个任务"""
        self.tasks_completed_today += 1
        self.total_tasks_completed += 1
        self.set_online()
