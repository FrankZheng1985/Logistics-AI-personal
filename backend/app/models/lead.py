"""
线索数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, DateTime, Text, Enum, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
import uuid
import enum

from app.models.database import Base


class LeadSource(str, enum.Enum):
    """线索来源"""
    WEIBO = "weibo"           # 微博
    ZHIHU = "zhihu"           # 知乎
    TIEBA = "tieba"           # 贴吧
    WECHAT = "wechat"         # 微信
    GOOGLE = "google"         # Google搜索
    YOUTUBE = "youtube"       # YouTube
    FACEBOOK = "facebook"     # Facebook
    LINKEDIN = "linkedin"     # LinkedIn
    B2B_ALIBABA = "alibaba"   # 阿里巴巴
    B2B_1688 = "1688"         # 1688
    MANUAL = "manual"         # 手动录入
    OTHER = "other"           # 其他


class LeadStatus(str, enum.Enum):
    """线索状态"""
    NEW = "new"               # 新线索
    CONTACTED = "contacted"   # 已联系
    FOLLOWING = "following"   # 跟进中
    CONVERTED = "converted"   # 已转化（成为客户）
    INVALID = "invalid"       # 无效线索
    ARCHIVED = "archived"     # 已归档


class LeadIntentLevel(str, enum.Enum):
    """意向等级"""
    HIGH = "high"             # 高意向
    MEDIUM = "medium"         # 中意向
    LOW = "low"               # 低意向
    UNKNOWN = "unknown"       # 未知


class Lead(Base):
    """线索表"""
    __tablename__ = "leads"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # 基本信息
    name: Mapped[Optional[str]] = mapped_column(String(100))
    company: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    wechat: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 线索来源
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, name='lead_source', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LeadSource.OTHER
    )
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_content: Mapped[Optional[str]] = mapped_column(Text)  # 原始内容
    content: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # 详细内容（JSON格式）
    
    # 状态和意向
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name='lead_status', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LeadStatus.NEW
    )
    intent_level: Mapped[LeadIntentLevel] = mapped_column(
        Enum(LeadIntentLevel, name='lead_intent_level', create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=LeadIntentLevel.UNKNOWN
    )
    intent_score: Mapped[int] = mapped_column(Integer, default=0)
    
    # AI分析结果
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)  # AI置信度
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)  # AI摘要
    ai_suggestion: Mapped[Optional[str]] = mapped_column(Text)  # 跟进建议
    
    # 需求标签
    needs: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    
    # 额外数据
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    
    # 跟进记录
    last_contact_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    
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
        return f"<Lead {self.name or 'Unknown'} from {self.source.value}>"
