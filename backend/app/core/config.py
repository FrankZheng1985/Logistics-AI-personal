"""
应用配置管理
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    APP_NAME: str = "物流获客AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://admin:password@localhost:5432/logistics_ai"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT认证
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7天
    
    # AI模型配置
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # 通义千问配置（主力模型）
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODEL: str = "qwen-max"  # 升级到 qwen-max（最强版本）
    
    # DeepSeek配置（代码专家）
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    
    # 腾讯混元配置（腾讯云原生，稳定）
    HUNYUAN_SECRET_ID: Optional[str] = None  # 可复用 TENCENT_SECRET_ID
    HUNYUAN_SECRET_KEY: Optional[str] = None  # 可复用 TENCENT_SECRET_KEY
    HUNYUAN_MODEL: str = "hunyuan-pro"  # 可选: hunyuan-lite, hunyuan-standard, hunyuan-pro
    
    # OpenRouter 中转配置（访问 Claude/Gemini/GPT）
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_CLAUDE_MODEL: str = "anthropic/claude-3.5-sonnet"  # Claude 3.5
    OPENROUTER_GEMINI_MODEL: str = "google/gemini-pro-1.5"  # Gemini 1.5 Pro
    OPENROUTER_GPT4_MODEL: str = "openai/gpt-4-turbo"  # GPT-4 Turbo
    
    AI_PRIMARY_MODEL: str = "qwen-max"
    AI_FALLBACK_MODEL: str = "deepseek-chat"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 4000  # 增加 token 限制
    
    # 可灵视频API (Kling AI)
    KELING_API_KEY: Optional[str] = None  # 旧版单密钥（可选）
    KELING_ACCESS_KEY: Optional[str] = None  # Access Key
    KELING_SECRET_KEY: Optional[str] = None  # Secret Key
    KELING_API_URL: str = "https://api.klingai.com"
    
    # 素材采集API（小采使用）
    PEXELS_API_KEY: Optional[str] = None  # Pexels免费素材API
    PIXABAY_API_KEY: Optional[str] = None  # Pixabay免费素材API
    
    # 视频后期处理配置
    VIDEO_POST_PROCESSING: bool = True  # 是否启用后期处理（文字叠加、配音、背景音乐）
    VIDEO_TTS_VOICE: str = "zh_female"  # 默认TTS语音: zh_male, zh_female, en_male, en_female
    VIDEO_DEFAULT_BGM: str = "bgm_corporate"  # 默认背景音乐类型
    VIDEO_OUTPUT_DIR: str = "/tmp/video_output"  # 视频输出目录
    
    # 企业微信配置 - 小销（销售客服）
    WECHAT_CORP_ID: Optional[str] = None
    WECHAT_AGENT_ID: Optional[str] = None
    WECHAT_SECRET: Optional[str] = None
    WECHAT_TOKEN: Optional[str] = None
    WECHAT_ENCODING_AES_KEY: Optional[str] = None
    NOTIFY_WECHAT_USERS: str = ""  # 接收通知的企业微信用户ID，逗号分隔
    
    # 企业微信配置 - 小析2（群情报员/菠萝蜜）
    WECHAT_ANALYST2_AGENT_ID: Optional[str] = None
    WECHAT_ANALYST2_SECRET: Optional[str] = None
    WECHAT_ANALYST2_TOKEN: Optional[str] = None
    WECHAT_ANALYST2_ENCODING_AES_KEY: Optional[str] = None
    
    # 企业微信配置 - 小欧间谍（欧洲海关监控员）
    WECHAT_EU_MONITOR_AGENT_ID: Optional[str] = None
    WECHAT_EU_MONITOR_SECRET: Optional[str] = None
    WECHAT_EU_MONITOR_TOKEN: Optional[str] = None
    WECHAT_EU_MONITOR_ENCODING_AES_KEY: Optional[str] = None
    
    # 企业微信配置 - 小调（AI调度主管）
    WECHAT_COORDINATOR_AGENT_ID: Optional[str] = None
    WECHAT_COORDINATOR_SECRET: Optional[str] = None
    WECHAT_COORDINATOR_TOKEN: Optional[str] = None
    WECHAT_COORDINATOR_ENCODING_AES_KEY: Optional[str] = None
    WECHAT_COORDINATOR_ADMIN_USERS: str = ""  # 可以给小调发任务的管理员用户ID，逗号分隔
    
    # 邮件配置
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFY_EMAIL: str = ""  # 接收通知的邮箱
    EMAIL_SENDER_NAME: str = "物流获客AI"
    
    # 腾讯云配置（统一凭证，用于COS、ASR等服务）
    TENCENT_SECRET_ID: Optional[str] = None
    TENCENT_SECRET_KEY: Optional[str] = None
    
    # 腾讯云COS配置
    COS_SECRET_ID: Optional[str] = None  # 如不设置，使用TENCENT_SECRET_ID
    COS_SECRET_KEY: Optional[str] = None  # 如不设置，使用TENCENT_SECRET_KEY
    COS_BUCKET: Optional[str] = None
    COS_REGION: str = "ap-guangzhou"
    
    # Serper API配置（Google搜索）
    SERPER_API_KEY: Optional[str] = None
    
    # Apple CalDAV 配置（Maria日历直写）
    APPLE_CALDAV_USERNAME: Optional[str] = None  # Apple ID 邮箱
    APPLE_CALDAV_PASSWORD: Optional[str] = None  # App专用密码
    APPLE_CALDAV_URL: str = "https://caldav.icloud.com"  # CalDAV服务器
    APPLE_CALDAV_CALENDAR_NAME: Optional[str] = None  # 指定操作的日历名称（为空则用默认日历）
    
    # Notion 集成配置
    NOTION_API_KEY: Optional[str] = None
    NOTION_ROOT_PAGE_ID: Optional[str] = None  # 根页面ID，Maria创建的页面默认放在这里
    
    # GitHub 配置（小码部署使用）
    GITHUB_TOKEN: Optional[str] = None  # Personal Access Token，需要repo权限
    GITHUB_USERNAME: Optional[str] = None  # GitHub用户名，用于GitHub Pages部署
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 意向评分配置
    INTENT_SCORE_ASK_PRICE: int = 25
    INTENT_SCORE_PROVIDE_CARGO: int = 20
    INTENT_SCORE_ASK_TRANSIT: int = 15
    INTENT_SCORE_MULTIPLE_INTERACTIONS: int = 30
    INTENT_SCORE_LEAVE_CONTACT: int = 50
    INTENT_SCORE_EXPRESS_INTEREST: int = 40
    INTENT_SCORE_JUST_ASKING: int = -10
    
    # 高意向通知阈值
    HIGH_INTENT_THRESHOLD: int = 60
    
    # 定时任务配置
    SCHEDULER_ENABLED: bool = True
    DAILY_FOLLOW_CHECK_HOUR: int = 9  # 每日跟进检查时间（小时）
    DAILY_SUMMARY_HOUR: int = 18  # 每日汇总时间（小时）
    
    # 跟进策略配置
    FOLLOW_INTERVAL_S: int = 1   # S级客户跟进间隔（天）
    FOLLOW_INTERVAL_A: int = 2   # A级客户跟进间隔（天）
    FOLLOW_INTERVAL_B: int = 5   # B级客户跟进间隔（天）
    FOLLOW_INTERVAL_C: int = 15  # C级客户跟进间隔（天）
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
