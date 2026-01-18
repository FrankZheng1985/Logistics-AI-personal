"""
邮箱账户管理API
提供邮箱账户的增删改查和邮件查询功能
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from loguru import logger

from app.services.multi_email_service import multi_email_service

router = APIRouter(prefix="/email-accounts", tags=["邮箱账户管理"])


# ==================== 请求模型 ====================

class EmailAccountCreate(BaseModel):
    """创建邮箱账户请求"""
    name: str  # 邮箱别名
    email_address: EmailStr
    provider: str = "other"  # qq_enterprise/aliyun/163/gmail/outlook/qq/other
    
    # IMAP配置（可选，如果选择已知服务商则自动填充）
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_ssl: bool = True
    
    # SMTP配置（可选）
    smtp_host: Optional[str] = None
    smtp_port: int = 465
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_ssl: bool = True


class EmailAccountUpdate(BaseModel):
    """更新邮箱账户请求"""
    name: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_ssl: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_ssl: Optional[bool] = None
    sync_enabled: Optional[bool] = None
    sync_interval_minutes: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class SendEmailRequest(BaseModel):
    """发送邮件请求"""
    account_id: str  # 使用哪个邮箱账户发送
    to_emails: List[str]
    subject: str
    body_html: str
    body_text: Optional[str] = None
    reply_to_id: Optional[str] = None  # 回复的邮件ID


# ==================== 邮箱账户管理 ====================

@router.get("", summary="获取邮箱账户列表")
async def get_email_accounts(
    active_only: bool = Query(True, description="是否只返回启用的账户")
):
    """获取所有邮箱账户"""
    accounts = await multi_email_service.get_email_accounts(active_only=active_only)
    return {
        "success": True,
        "data": accounts,
        "total": len(accounts)
    }


@router.get("/providers", summary="获取支持的邮箱服务商")
async def get_providers():
    """获取支持的邮箱服务商及其默认配置"""
    providers = []
    for key, config in multi_email_service.PROVIDER_CONFIGS.items():
        providers.append({
            "id": key,
            "name": {
                "qq_enterprise": "腾讯企业邮",
                "aliyun": "阿里企业邮",
                "163": "网易163邮箱",
                "gmail": "Gmail",
                "outlook": "Outlook/Office365",
                "qq": "QQ邮箱"
            }.get(key, key),
            "config": config
        })
    
    return {
        "success": True,
        "data": providers
    }


@router.post("", summary="添加邮箱账户")
async def add_email_account(request: EmailAccountCreate):
    """添加新的邮箱账户"""
    result = await multi_email_service.add_email_account(
        name=request.name,
        email_address=request.email_address,
        provider=request.provider,
        imap_host=request.imap_host,
        imap_port=request.imap_port,
        imap_user=request.imap_user,
        imap_password=request.imap_password,
        smtp_host=request.smtp_host,
        smtp_port=request.smtp_port,
        smtp_user=request.smtp_user,
        smtp_password=request.smtp_password,
        imap_ssl=request.imap_ssl,
        smtp_ssl=request.smtp_ssl
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return {
        "success": True,
        "message": "邮箱账户添加成功",
        "data": {"account_id": result["account_id"]}
    }


@router.get("/{account_id}", summary="获取邮箱账户详情")
async def get_email_account(account_id: str):
    """获取单个邮箱账户详情"""
    account = await multi_email_service.get_email_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="邮箱账户不存在")
    
    return {
        "success": True,
        "data": account
    }


@router.put("/{account_id}", summary="更新邮箱账户")
async def update_email_account(account_id: str, request: EmailAccountUpdate):
    """更新邮箱账户配置"""
    update_data = request.model_dump(exclude_none=True)
    
    if not update_data:
        return {"success": True, "message": "无需更新"}
    
    success = await multi_email_service.update_email_account(account_id, **update_data)
    
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")
    
    return {
        "success": True,
        "message": "邮箱账户更新成功"
    }


@router.delete("/{account_id}", summary="删除邮箱账户")
async def delete_email_account(account_id: str):
    """删除邮箱账户"""
    success = await multi_email_service.delete_email_account(account_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return {
        "success": True,
        "message": "邮箱账户已删除"
    }


@router.post("/{account_id}/test", summary="测试邮箱连接")
async def test_email_account(account_id: str):
    """测试邮箱账户的IMAP和SMTP连接"""
    result = await multi_email_service.test_email_account(account_id)
    
    return {
        "success": result["success"],
        "imap": result.get("imap", {}),
        "smtp": result.get("smtp", {}),
        "message": "连接测试成功" if result["success"] else "连接测试失败"
    }


# ==================== 邮件同步 ====================

@router.post("/{account_id}/sync", summary="同步邮箱邮件")
async def sync_account_emails(
    account_id: str,
    days_back: int = Query(7, description="同步最近几天的邮件"),
    max_emails: int = Query(100, description="最多同步多少封邮件")
):
    """同步指定邮箱账户的邮件"""
    result = await multi_email_service.sync_account_emails(
        account_id=account_id,
        days_back=days_back,
        max_emails=max_emails
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {
        "success": True,
        "message": f"同步完成，新增 {result['new_count']} 封邮件",
        "data": result
    }


@router.post("/sync-all", summary="同步所有邮箱")
async def sync_all_accounts():
    """同步所有启用同步的邮箱账户"""
    result = await multi_email_service.sync_all_accounts()
    
    return {
        "success": True,
        "message": f"已同步 {result['total_accounts']} 个邮箱账户",
        "data": result
    }


# ==================== 邮件查询 ====================

@router.get("/emails/unread", summary="获取未读邮件摘要")
async def get_unread_summary():
    """获取所有邮箱的未读邮件摘要"""
    summary = await multi_email_service.get_unread_summary()
    
    return {
        "success": True,
        "data": summary
    }


@router.get("/emails/list", summary="获取未读邮件列表")
async def get_unread_emails(
    account_id: Optional[str] = Query(None, description="邮箱账户ID（不传则查所有）"),
    limit: int = Query(20, description="返回数量限制")
):
    """获取未读邮件列表"""
    emails = await multi_email_service.get_unread_emails(
        account_id=account_id,
        limit=limit
    )
    
    return {
        "success": True,
        "data": emails,
        "total": len(emails)
    }


@router.get("/emails/{email_id}", summary="获取邮件详情")
async def get_email_detail(email_id: str):
    """获取单封邮件的详细内容"""
    email = await multi_email_service.get_email_detail(email_id)
    
    if not email:
        raise HTTPException(status_code=404, detail="邮件不存在")
    
    # 自动标记为已读
    await multi_email_service.mark_email_read(email_id)
    
    return {
        "success": True,
        "data": email
    }


@router.post("/emails/{email_id}/mark-read", summary="标记邮件已读")
async def mark_email_read(email_id: str):
    """标记邮件为已读"""
    success = await multi_email_service.mark_email_read(email_id)
    
    return {
        "success": success,
        "message": "已标记为已读" if success else "操作失败"
    }


@router.post("/emails/{email_id}/mark-important", summary="标记邮件重要")
async def mark_email_important(
    email_id: str,
    important: bool = Query(True, description="是否重要")
):
    """标记邮件为重要"""
    success = await multi_email_service.mark_email_important(email_id, important)
    
    return {
        "success": success,
        "message": "已标记为重要" if success else "操作失败"
    }


# ==================== 邮件发送 ====================

@router.post("/send", summary="发送邮件")
async def send_email(request: SendEmailRequest):
    """通过指定邮箱账户发送邮件"""
    result = await multi_email_service.send_email(
        account_id=request.account_id,
        to_emails=request.to_emails,
        subject=request.subject,
        body_html=request.body_html,
        body_text=request.body_text,
        reply_to_id=request.reply_to_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {
        "success": True,
        "message": "邮件发送成功"
    }
