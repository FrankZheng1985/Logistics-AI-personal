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


class SMTPConfig(BaseModel):
    """SMTP邮件配置"""
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 465
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    sender_name: Optional[str] = "物流智能体"


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


# =====================================================
# SMTP邮件配置
# =====================================================

@router.get("/smtp")
async def get_smtp_settings():
    """获取SMTP邮件配置"""
    try:
        # 优先从数据库读取
        smtp_config = await get_setting("smtp")
        
        # 如果数据库没有，从环境变量读取
        if not smtp_config:
            smtp_config = {
                "smtp_host": os.getenv("SMTP_HOST", ""),
                "smtp_port": int(os.getenv("SMTP_PORT", "465")),
                "smtp_user": os.getenv("SMTP_USER", ""),
                "smtp_password": "",  # 不返回密码
                "sender_name": os.getenv("EMAIL_SENDER_NAME", "物流智能体")
            }
        else:
            # 不返回密码明文
            smtp_config["smtp_password"] = "********" if smtp_config.get("smtp_password") else ""
        
        # 检查是否已配置
        is_configured = bool(
            smtp_config.get("smtp_host") and 
            smtp_config.get("smtp_user") and 
            (smtp_config.get("smtp_password") or os.getenv("SMTP_PASSWORD"))
        )
        
        return {
            "success": True,
            "data": smtp_config,
            "configured": is_configured
        }
    except Exception as e:
        logger.error(f"获取SMTP配置失败: {e}")
        return {
            "success": False,
            "data": {},
            "configured": False
        }


@router.put("/smtp")
async def update_smtp_settings(config: SMTPConfig):
    """更新SMTP邮件配置"""
    try:
        data = config.model_dump(exclude_none=True)
        
        # 如果密码为空或是占位符，保留原密码
        if not data.get("smtp_password") or data.get("smtp_password") == "********":
            current = await get_setting("smtp")
            if current and current.get("smtp_password"):
                data["smtp_password"] = current["smtp_password"]
            else:
                # 如果数据库没有，检查环境变量
                env_password = os.getenv("SMTP_PASSWORD", "")
                if env_password:
                    data["smtp_password"] = env_password
        
        await save_setting("smtp", data)
        
        # 更新email_service的配置
        try:
            from app.services.email_service import email_service
            email_service.smtp_host = data.get("smtp_host", "")
            email_service.smtp_port = data.get("smtp_port", 465)
            email_service.smtp_user = data.get("smtp_user", "")
            email_service.smtp_password = data.get("smtp_password", "")
            email_service.sender_name = data.get("sender_name", "物流智能体")
            logger.info("邮件服务配置已更新")
        except Exception as e:
            logger.warning(f"更新邮件服务配置失败: {e}")
        
        logger.info("SMTP设置已保存")
        return {"success": True, "message": "SMTP配置已保存"}
    except Exception as e:
        logger.error(f"更新SMTP设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smtp/test")
async def test_smtp_connection():
    """测试SMTP连接"""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.utils import formataddr
    
    try:
        # 直接从数据库读取配置
        smtp_config = await get_setting("smtp")
        
        if not smtp_config:
            return {
                "success": False,
                "message": "SMTP未配置，请先填写配置信息"
            }
        
        smtp_host = smtp_config.get("smtp_host", "")
        smtp_port = smtp_config.get("smtp_port", 465)
        smtp_user = smtp_config.get("smtp_user", "")
        smtp_password = smtp_config.get("smtp_password", "")
        sender_name = smtp_config.get("sender_name", "物流智能体")
        
        logger.info(f"SMTP测试 - host: {smtp_host}, port: {smtp_port}, user: {smtp_user}, has_password: {bool(smtp_password)}")
        
        if not smtp_host or not smtp_user or not smtp_password:
            return {
                "success": False,
                "message": f"SMTP配置不完整: host={bool(smtp_host)}, user={bool(smtp_user)}, password={bool(smtp_password)}"
            }
        
        # 使用 email_service 发送测试邮件（带签名）
        from app.services.email_service import email_service
        
        # 先更新 email_service 的配置
        email_service.smtp_host = smtp_host
        email_service.smtp_port = smtp_port
        email_service.smtp_user = smtp_user
        email_service.smtp_password = smtp_password
        email_service.sender_name = sender_name
        
        to_email = smtp_user  # 发送给自己
        
        # 使用带签名的客户邮件格式发送测试
        result = await email_service.send_simple_customer_email(
            to_email=to_email,
            subject="📧 SMTP配置测试 - 邮件签名预览",
            body="这是一封测试邮件，用于验证SMTP配置是否正确。\n\n如果您收到这封邮件，说明邮件服务已正确配置，系统可以正常发送客户跟进邮件了。\n\n下方是邮件签名效果预览：",
            customer_name="测试用户"
        )
        
        if result.get("status") != "sent":
            raise Exception(result.get("message", "发送失败"))
        
        logger.info(f"SMTP测试邮件发送成功: {to_email}")
        
        return {
            "success": True,
            "message": f"测试邮件已发送至 {to_email}"
        }
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP认证失败: {e}")
        return {
            "success": False,
            "message": f"SMTP认证失败，请检查用户名和密码是否正确"
        }
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP连接失败: {e}")
        return {
            "success": False,
            "message": f"无法连接到SMTP服务器，请检查服务器地址和端口"
        }
    except Exception as e:
        logger.error(f"SMTP测试失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/smtp/signature-preview")
async def get_signature_preview():
    """获取邮件签名预览"""
    try:
        # 获取SMTP配置中的发件人名称
        smtp_config = await get_setting("smtp")
        sender_name = smtp_config.get("sender_name", "物流智能体") if smtp_config else "物流智能体"
        sender_email = smtp_config.get("smtp_user", "") if smtp_config else ""
        
        # 获取公司配置
        from app.models.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT config_data FROM company_config WHERE id = (SELECT MIN(id) FROM company_config)")
            )
            row = result.fetchone()
            
            company_name = ""
            contact_phone = ""
            contact_email = sender_email
            contact_wechat = ""
            address = ""
            company_website = ""
            brand_slogan = ""
            
            if row and row[0]:
                config = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                company_name = config.get("company_name", "")
                contact_phone = config.get("contact_phone", "")
                contact_email = config.get("contact_email", sender_email)
                contact_wechat = config.get("contact_wechat", "")
                address = config.get("address", "")
                company_website = config.get("company_website", "")
                brand_slogan = config.get("brand_slogan", "")
        
        # 构建 HTML 签名预览
        html_parts = [
            '<div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e0e0e0; font-size: 13px; color: #666; font-family: Arial, sans-serif;">'
        ]
        
        if brand_slogan:
            html_parts.append(f'<p style="margin: 0 0 10px 0; color: #333; font-style: italic;">"{brand_slogan}"</p>')
        
        html_parts.append(f'<p style="margin: 5px 0; font-size: 14px;"><strong style="color: #333;">{sender_name}</strong></p>')
        
        if company_name:
            html_parts.append(f'<p style="margin: 5px 0;">{company_name}</p>')
        
        if contact_phone:
            html_parts.append(f'<p style="margin: 5px 0;">📞 电话：{contact_phone}</p>')
        
        if contact_email:
            html_parts.append(f'<p style="margin: 5px 0;">📧 邮箱：{contact_email}</p>')
        
        if contact_wechat:
            html_parts.append(f'<p style="margin: 5px 0;">💬 微信：{contact_wechat}</p>')
        
        if address:
            html_parts.append(f'<p style="margin: 5px 0;">📍 地址：{address}</p>')
        
        if company_website:
            website_url = company_website if company_website.startswith('http') else f'https://{company_website}'
            html_parts.append(f'<p style="margin: 5px 0;">🌐 官网：<a href="{website_url}" style="color: #0066cc;">{company_website}</a></p>')
        
        html_parts.append('</div>')
        
        return {
            "success": True,
            "html": "\n".join(html_parts),
            "data": {
                "sender_name": sender_name,
                "company_name": company_name,
                "contact_phone": contact_phone,
                "contact_email": contact_email,
                "contact_wechat": contact_wechat,
                "address": address,
                "company_website": company_website,
                "brand_slogan": brand_slogan
            }
        }
    except Exception as e:
        logger.error(f"获取签名预览失败: {e}")
        return {
            "success": False,
            "html": "",
            "data": {},
            "error": str(e)
        }


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
