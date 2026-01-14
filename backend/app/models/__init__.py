# SQLAlchemy 数据模型
from app.models.database import Base, engine, AsyncSessionLocal, get_db, init_db
from app.models.customer import Customer, IntentLevel, CustomerSource
from app.models.conversation import Conversation, AgentType, MessageType
from app.models.task import AITask, TaskStatus
from app.models.video import Video, VideoStatus
from app.models.agent import AIAgent, AgentStatus
from app.models.company_config import CompanyConfig
from app.models.lead import Lead, LeadSource, LeadStatus, LeadIntentLevel
from app.models.follow_record import FollowRecord, FollowType, FollowResult, FollowChannel

__all__ = [
    # 数据库
    "Base",
    "engine", 
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    # 模型
    "Customer",
    "Conversation",
    "AITask",
    "Video",
    "AIAgent",
    "CompanyConfig",
    "Lead",
    "FollowRecord",
    # 枚举
    "IntentLevel",
    "CustomerSource",
    "AgentType",
    "MessageType",
    "TaskStatus",
    "VideoStatus",
    "AgentStatus",
    "LeadSource",
    "LeadStatus",
    "LeadIntentLevel",
    "FollowType",
    "FollowResult",
    "FollowChannel",
]
