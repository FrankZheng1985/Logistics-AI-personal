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
    
    AI_PRIMARY_MODEL: str = "qwen-plus"
    AI_FALLBACK_MODEL: str = "gpt-4-turbo-preview"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2000
    
    # 可灵视频API
    KELING_API_KEY: Optional[str] = None
    KELING_API_URL: str = "https://api.keling.ai/v1"
    
    # 企业微信配置
    WECHAT_CORP_ID: Optional[str] = None
    WECHAT_AGENT_ID: Optional[str] = None
    WECHAT_SECRET: Optional[str] = None
    WECHAT_TOKEN: Optional[str] = None
    WECHAT_ENCODING_AES_KEY: Optional[str] = None
    
    # 腾讯云COS配置
    COS_SECRET_ID: Optional[str] = None
    COS_SECRET_KEY: Optional[str] = None
    COS_BUCKET: Optional[str] = None
    COS_REGION: str = "ap-guangzhou"
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
