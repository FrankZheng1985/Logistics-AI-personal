"""
跟进记录数据模型
记录每次客户跟进的完整轨迹
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum

from app.models.database import Base


class FollowType(str, enum.Enum):
    """跟进类型"""
    FIRST_CONTACT = "first_contact"      # 首次联系
    DAILY_FOLLOW = "daily_follow"        # 日常跟进
    INTENT_TRACK = "intent_track"        # 意向跟踪
    REACTIVATE = "reactivate"            # 激活沉默客户
    PROMOTION = "promotion"              # 促销推送
    AFTER_SALE = "after_sale"            # 售后跟进
    OTHER = "other"                      # 其他


class FollowResult(str, enum.Enum):
    """跟进结果"""
    REPLIED = "replied"                  # 客户已回复
    NO_REPLY = "no_reply"                # 未回复
    INTERESTED = "interested"            # 表达兴趣
    NOT_INTERESTED = "not_interested"    # 无兴趣
    DEAL_PROGRESS = "deal_progress"      # 成交进展
    DEAL_CLOSED = "deal_closed"          # 已成交
    LOST = "lost"                        # 已流失


class FollowChannel(str, enum.Enum):
    """跟进渠道"""
    WECHAT = "wechat"                    # 企业微信
    PHONE = "phone"                      # 电话
    EMAIL = "email"                      # 邮件
    WEBSITE = "website"                  # 网站客服
    DOUYIN = "douyin"                    # 抖音私信
    XIAOHONGSHU = "xiaohongshu"          # 小红书
    SYSTEM = "system"                    # 系统自动
    OTHER = "other"                      # 其他


class FollowRecord(Base):
    """跟进记录表"""
    __tablename__ = "follow_records"
    
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
        nullable=False,
        index=True
    )
    
    # 跟进信息
    follow_type: Mapped[FollowType] = mapped_column(
        Enum(FollowType, name='follow_type', create_type=False),
        default=FollowType.DAILY_FOLLOW
    )
    
    channel: Mapped[FollowChannel] = mapped_column(
        Enum(FollowChannel, name='follow_channel', create_type=False),
        default=FollowChannel.WECHAT
    )
    
    # 执行者 (AI员工类型或人工)
    executor_type: Mapped[str] = mapped_column(String(50), default="sales")  # sales/follow/manual
    executor_name: Mapped[Optional[str]] = mapped_column(String(100))  # 小销/小跟/张三
    
    # 跟进内容
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 发送的消息内容
    customer_reply: Mapped[Optional[str]] = mapped_column(Text)  # 客户回复内容
    
    # 跟进结果
    result: Mapped[Optional[FollowResult]] = mapped_column(
        Enum(FollowResult, name='follow_result', create_type=False),
        nullable=True
    )
    result_note: Mapped[Optional[str]] = mapped_column(Text)  # 结果备注
    
    # 意向变化
    intent_before: Mapped[int] = mapped_column(Integer, default=0)  # 跟进前意向分
    intent_after: Mapped[int] = mapped_column(Integer, default=0)   # 跟进后意向分
    intent_level_before: Mapped[Optional[str]] = mapped_column(String(1))  # 跟进前等级
    intent_level_after: Mapped[Optional[str]] = mapped_column(String(1))   # 跟进后等级
    
    # 下次跟进计划
    next_follow_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_follow_note: Mapped[Optional[str]] = mapped_column(String(500))  # 下次跟进备注
    
    # 关联对话ID (如果是从对话产生的)
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    
    # 元数据
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow
    )
    
    # 关系
    customer = relationship("Customer", backref="follow_records")
    
    def __repr__(self):
        return f"<FollowRecord {self.follow_type.value} - {self.customer_id}>"
    
    @property
    def intent_delta(self) -> int:
        """意向分数变化"""
        return self.intent_after - self.intent_before
    
    @property
    def is_positive_result(self) -> bool:
        """是否为积极结果"""
        return self.result in [
            FollowResult.REPLIED, 
            FollowResult.INTERESTED, 
            FollowResult.DEAL_PROGRESS, 
            FollowResult.DEAL_CLOSED
        ]
