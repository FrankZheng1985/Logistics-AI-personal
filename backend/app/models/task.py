"""
AI任务数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.models.database import Base
from app.models.conversation import AgentType


class TaskStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"        # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


class AITask(Base):
    """AI任务表"""
    __tablename__ = "ai_tasks"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # 任务信息
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), 
        default=TaskStatus.PENDING
    )
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10，越小越优先
    
    # 关联
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("customers.id")
    )
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("ai_tasks.id")
    )
    
    # 输入输出
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    output_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # 执行信息
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
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
    customer = relationship("Customer", back_populates="tasks")
    parent_task = relationship("AITask", remote_side=[id], backref="subtasks")
    video = relationship("Video", back_populates="task", uselist=False)
    
    def __repr__(self):
        return f"<AITask {self.task_type} ({self.status.value})>"
    
    def start(self):
        """开始任务"""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.utcnow()
    
    def complete(self, output: Dict[str, Any]):
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.output_data = output
        self.completed_at = datetime.utcnow()
    
    def fail(self, error: str):
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()
    
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.retry_count < self.max_retries
