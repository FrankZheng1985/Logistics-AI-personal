"""
视频数据模型
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, BigInteger, DateTime, Text, Enum, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.models.database import Base


class VideoStatus(str, enum.Enum):
    """视频状态"""
    DRAFT = "draft"          # 草稿
    GENERATING = "generating"  # 生成中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 生成失败


class Video(Base):
    """视频表"""
    __tablename__ = "videos"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # 基本信息
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    video_type: Mapped[Optional[str]] = mapped_column(String(50))  # ad, intro, route等
    
    # 内容
    script: Mapped[Optional[str]] = mapped_column(Text)
    keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(50)))
    
    # 文件信息
    video_url: Mapped[Optional[str]] = mapped_column(String(500))
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500))
    duration: Mapped[Optional[int]] = mapped_column(Integer)  # 秒
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)  # 字节
    
    # 状态
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus), 
        default=VideoStatus.DRAFT
    )
    
    # 关联
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("ai_tasks.id")
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id")
    )
    
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
    task = relationship("AITask", back_populates="video")
    
    def __repr__(self):
        return f"<Video {self.title} ({self.status.value})>"
