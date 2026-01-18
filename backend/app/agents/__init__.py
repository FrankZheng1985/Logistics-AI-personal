# AI员工模块
from app.agents.base import BaseAgent, AgentRegistry
from app.agents.coordinator import coordinator, coordinator_agent, CoordinatorAgent
from app.agents.sales_agent import sales_agent, SalesAgent
from app.agents.analyst import analyst_agent, AnalystAgent
from app.agents.copywriter import copywriter_agent, CopywriterAgent
from app.agents.video_creator import video_creator_agent, VideoCreatorAgent
from app.agents.follow_agent import follow_agent, FollowAgent
from app.agents.lead_hunter import lead_hunter_agent, LeadHunterAgent
from app.agents.eu_customs_monitor import eu_customs_monitor_agent, EUCustomsMonitorAgent
from app.agents.assistant_agent import assistant_agent, AssistantAgent

__all__ = [
    # 基类
    "BaseAgent",
    "AgentRegistry",
    # Agent类
    "CoordinatorAgent",
    "SalesAgent",
    "AnalystAgent",
    "CopywriterAgent",
    "VideoCreatorAgent",
    "FollowAgent",
    "LeadHunterAgent",
    "EUCustomsMonitorAgent",
    "AssistantAgent",
    # 单例实例
    "coordinator",
    "coordinator_agent",  # 兼容旧代码
    "sales_agent",
    "analyst_agent",
    "copywriter_agent",
    "video_creator_agent",
    "follow_agent",
    "lead_hunter_agent",
    "eu_customs_monitor_agent",
    "assistant_agent",
]

# AI员工团队介绍
AI_TEAM = {
    "coordinator": {
        "name": "小调",
        "role": "AI调度主管",
        "description": "负责任务分配、流程协调、异常处理",
    },
    "video_creator": {
        "name": "小视",
        "role": "视频创作员",
        "description": "生成物流广告视频、产品展示视频",
    },
    "copywriter": {
        "name": "小文",
        "role": "文案策划",
        "description": "广告文案、朋友圈文案、视频脚本",
    },
    "sales": {
        "name": "小销",
        "role": "销售客服",
        "description": "首次接待、解答咨询、收集需求",
    },
    "follow": {
        "name": "小跟",
        "role": "跟进专员",
        "description": "老客户维护、意向客户跟进、促成转化",
    },
    "analyst": {
        "name": "小析",
        "role": "客户分析师",
        "description": "意向评分、客户画像、数据报表",
    },
    "lead_hunter": {
        "name": "小猎",
        "role": "线索猎手",
        "description": "从互联网搜索潜在客户线索、发现商机",
    },
    "eu_customs_monitor": {
        "name": "小欧间谍",
        "role": "欧洲海关监控员",
        "description": "监控欧洲海关新闻、反倾销、关税调整、进口政策等",
    },
    "assistant": {
        "name": "小助",
        "role": "个人助理",
        "description": "日程管理、会议纪要、邮件管理、ERP数据跟踪",
    },
}
