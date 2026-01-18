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
    
    # 通义千问配置（推荐）
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODEL: str = "qwen-plus"  # 可选: qwen-turbo, qwen-plus, qwen-max
    
    # DeepSeek配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    
    AI_PRIMARY_MODEL: str = "qwen-plus"
    AI_FALLBACK_MODEL: str = "gpt-4-turbo-preview"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2000
    
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
    
    # 邮件配置
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFY_EMAIL: str = ""  # 接收通知的邮箱
    EMAIL_SENDER_NAME: str = "物流获客AI"
    
    # 腾讯云COS配置
    COS_SECRET_ID: Optional[str] = None
    COS_SECRET_KEY: Optional[str] = None
    COS_BUCKET: Optional[str] = None
    COS_REGION: str = "ap-guangzhou"
    
    # Serper API配置（Google搜索）
    SERPER_API_KEY: Optional[str] = None
    
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
