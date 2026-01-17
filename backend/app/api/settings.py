"""
系统设置API
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from loguru import logger
import json
import os

from app.models.database import AsyncSessionLocal
from sqlalchemy import text

router = APIRouter(prefix="/settings", tags=["系统设置"])


class CompanyConfig(BaseModel):
    company_name: Optional[str] = None
    company_intro: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    contact_wechat: Optional[str] = None
    address: Optional[str] = None
    advantages: Optional[List[str]] = None


class NotificationConfig(BaseModel):
    high_intent_threshold: Optional[int] = 60
    enable_wechat_notify: Optional[bool] = True
    enable_email_notify: Optional[bool] = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"


class AIConfig(BaseModel):
    model_name: Optional[str] = "qwen-max"
    temperature: Optional[float] = 0.7


class SettingsResponse(BaseModel):
    company: dict
    notification: dict
    ai: dict
    updated_at: Optional[str] = None


# 设置存储（使用数据库）
async def get_setting(key: str) -> dict:
    """获取设置"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT value FROM system_settings WHERE key = :key"),
                {"key": key}
            )
            row = result.fetchone()
            if row and row[0]:
                return json.loads(row[0]) if isinstance(row[0], str) else row[0]
            return {}
    except Exception as e:
        logger.warning(f"获取设置失败 {key}: {e}")
        return {}


async def save_setting(key: str, value: dict):
    """保存设置"""
    try:
        async with AsyncSessionLocal() as db:
            # 使用 UPSERT
            await db.execute(
                text("""
                    INSERT INTO system_settings (key, value, updated_at)
                    VALUES (:key, :value, NOW())
                    ON CONFLICT (key) DO UPDATE SET value = :value, updated_at = NOW()
                """),
                {"key": key, "value": json.dumps(value)}
            )
            await db.commit()
    except Exception as e:
        logger.error(f"保存设置失败 {key}: {e}")
        raise


@router.get("", response_model=SettingsResponse)
async def get_all_settings():
    """获取所有设置"""
    try:
        company = await get_setting("company")
        notification = await get_setting("notification")
        ai = await get_setting("ai")
        
        # 获取更新时间
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT MAX(updated_at) FROM system_settings")
            )
            row = result.fetchone()
            updated_at = row[0].isoformat() if row and row[0] else None
        
        return SettingsResponse(
            company=company or {},
            notification=notification or {
                "high_intent_threshold": 60,
                "enable_wechat_notify": True,
                "enable_email_notify": False,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00"
            },
            ai=ai or {
                "model_name": "qwen-max",
                "temperature": 0.7
            },
            updated_at=updated_at
        )
    except Exception as e:
        logger.error(f"获取设置失败: {e}")
        # 返回默认值
        return SettingsResponse(
            company={},
            notification={
                "high_intent_threshold": 60,
                "enable_wechat_notify": True,
                "enable_email_notify": False
            },
            ai={
                "model_name": "qwen-max",
                "temperature": 0.7
            }
        )


@router.put("/company")
async def update_company_settings(config: CompanyConfig):
    """更新公司信息设置"""
    try:
        data = config.model_dump(exclude_none=True)
        current = await get_setting("company")
        merged = {**current, **data}
        await save_setting("company", merged)
        
        logger.info("公司设置已更新")
        return {"message": "公司信息已保存", "data": merged}
    except Exception as e:
        logger.error(f"更新公司设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notification")
async def update_notification_settings(config: NotificationConfig):
    """更新通知设置"""
    try:
        data = config.model_dump(exclude_none=True)
        current = await get_setting("notification")
        merged = {**current, **data}
        await save_setting("notification", merged)
        
        logger.info("通知设置已更新")
        return {"message": "通知设置已保存", "data": merged}
    except Exception as e:
        logger.error(f"更新通知设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ai")
async def update_ai_settings(config: AIConfig):
    """更新AI设置"""
    try:
        data = config.model_dump(exclude_none=True)
        current = await get_setting("ai")
        merged = {**current, **data}
        await save_setting("ai", merged)
        
        logger.info("AI设置已更新")
        return {"message": "AI设置已保存", "data": merged}
    except Exception as e:
        logger.error(f"更新AI设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-all")
async def save_all_settings(
    company: Optional[CompanyConfig] = None,
    notification: Optional[NotificationConfig] = None,
    ai: Optional[AIConfig] = None
):
    """批量保存所有设置"""
    try:
        if company:
            data = company.model_dump(exclude_none=True)
            current = await get_setting("company")
            await save_setting("company", {**current, **data})
        
        if notification:
            data = notification.model_dump(exclude_none=True)
            current = await get_setting("notification")
            await save_setting("notification", {**current, **data})
        
        if ai:
            data = ai.model_dump(exclude_none=True)
            current = await get_setting("ai")
            await save_setting("ai", {**current, **data})
        
        logger.info("所有设置已保存")
        return {"message": "设置已保存"}
    except Exception as e:
        logger.error(f"保存设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def mask_api_key(key: str, show_chars: int = 4) -> str:
    """对API密钥进行部分隐藏处理"""
    if not key:
        return ""
    if len(key) <= show_chars * 2:
        return key
    return f"{key[:show_chars]}{'*' * (len(key) - show_chars * 2)}{key[-show_chars:]}"


@router.get("/api-keys")
async def get_api_keys():
    """获取已配置的API密钥（部分隐藏显示）"""
    try:
        # 从环境变量读取API密钥
        keys = {
            "keling_access_key": os.getenv("KELING_ACCESS_KEY", ""),
            "keling_secret_key": os.getenv("KELING_SECRET_KEY", ""),
            "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY", ""),
            "serper_api_key": os.getenv("SERPER_API_KEY", ""),
            "pexels_api_key": os.getenv("PEXELS_API_KEY", ""),
            "pixabay_api_key": os.getenv("PIXABAY_API_KEY", ""),
        }
        
        # 返回部分隐藏的密钥和配置状态
        result = {}
        for key_name, key_value in keys.items():
            result[key_name] = {
                "configured": bool(key_value),
                "masked_value": mask_api_key(key_value) if key_value else "",
                "full_value": key_value  # 完整值，前端可以选择是否显示
            }
        
        return result
    except Exception as e:
        logger.error(f"获取API密钥失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
