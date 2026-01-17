"""
邮件营销API
支持：发送客户邮件、管理邮件模板、查看发送记录
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from loguru import logger

from app.models.database import get_db
from app.models.customer import Customer
from app.services.email_service import email_service

router = APIRouter(prefix="/email", tags=["邮件营销"])


# =====================================================
# 请求/响应模型
# =====================================================

class SendEmailRequest(BaseModel):
    """发送邮件请求"""
    customer_id: UUID = Field(..., description="客户ID")
    template_id: Optional[str] = Field(None, description="模板ID（可选）")
    subject: Optional[str] = Field(None, description="邮件主题（不使用模板时必填）")
    content: Optional[str] = Field(None, description="邮件内容（不使用模板时必填）")
    variables: Optional[dict] = Field(default_factory=dict, description="模板变量")


class QuickSendRequest(BaseModel):
    """快速发送邮件（用于跟进）"""
    customer_id: UUID = Field(..., description="客户ID")
    purpose: str = Field("daily_follow", description="跟进目的: daily_follow, quote_follow, reactivate")
    custom_content: Optional[str] = Field(None, description="自定义内容（可选）")


class EmailTemplateCreate(BaseModel):
    """创建邮件模板"""
    name: str = Field(..., description="模板名称")
    template_type: str = Field("follow_up", description="模板类型")
    subject: str = Field(..., description="邮件主题")
    html_content: str = Field(..., description="HTML内容")
    text_content: Optional[str] = Field(None, description="纯文本内容")
    variables: List[str] = Field(default_factory=list, description="变量列表")


class EmailTemplateUpdate(BaseModel):
    """更新邮件模板"""
    name: Optional[str] = None
    subject: Optional[str] = None
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


# =====================================================
# 邮件发送接口
# =====================================================

@router.post("/send")
async def send_email_to_customer(
    request: SendEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    发送邮件给客户
    
    可以使用模板或直接提供内容
    """
    # 获取客户信息
    result = await db.execute(
        select(Customer).where(Customer.id == request.customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    if not customer.email:
        raise HTTPException(status_code=400, detail="客户未设置邮箱地址")
    
    # 准备变量
    variables = request.variables or {}
    variables.setdefault("customer_name", customer.name or "尊敬的客户")
    variables.setdefault("company", customer.company or "")
    
    # 发送邮件
    if request.template_id:
        # 使用模板发送
        send_result = await email_service.send_customer_email(
            customer_id=str(customer.id),
            to_email=customer.email,
            template_id=request.template_id,
            variables=variables,
            sender_type="manual",
            sender_name="人工"
        )
    else:
        # 使用自定义内容发送
        if not request.subject or not request.content:
            raise HTTPException(status_code=400, detail="不使用模板时必须提供邮件主题和内容")
        
        send_result = await email_service.send_customer_email(
            customer_id=str(customer.id),
            to_email=customer.email,
            subject=request.subject,
            html_content=request.content,
            variables=variables,
            sender_type="manual",
            sender_name="人工"
        )
    
    if send_result.get("status") == "sent":
        return {
            "success": True,
            "message": "邮件发送成功",
            "data": send_result
        }
    else:
        return {
            "success": False,
            "message": send_result.get("message", "发送失败"),
            "data": send_result
        }


@router.post("/quick-send")
async def quick_send_follow_email(
    request: QuickSendRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    快速发送跟进邮件
    
    用于小跟的自动跟进功能
    """
    # 获取客户信息
    result = await db.execute(
        select(Customer).where(Customer.id == request.customer_id)
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    
    if not customer.email:
        raise HTTPException(status_code=400, detail="客户未设置邮箱地址，无法发送邮件")
    
    # 发送跟进邮件
    send_result = await email_service.send_follow_email(
        customer_id=str(customer.id),
        to_email=customer.email,
        customer_name=customer.name or "尊敬的客户",
        purpose=request.purpose,
        custom_content=request.custom_content
    )
    
    if send_result.get("status") == "sent":
        # 更新客户最后联系时间
        await db.execute(
            text("""
                UPDATE customers 
                SET last_contact_at = NOW(), 
                    follow_count = follow_count + 1,
                    updated_at = NOW()
                WHERE id = :customer_id
            """),
            {"customer_id": str(customer.id)}
        )
        await db.commit()
        
        return {
            "success": True,
            "message": f"跟进邮件已发送至 {customer.email}",
            "data": send_result
        }
    else:
        return {
            "success": False,
            "message": send_result.get("message", "发送失败"),
            "data": send_result
        }


@router.post("/batch-send")
async def batch_send_emails(
    customer_ids: List[UUID],
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    批量发送邮件
    
    对多个客户使用同一模板发送邮件
    """
    # 验证模板存在
    template = await email_service.get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    results = {
        "total": len(customer_ids),
        "sent": 0,
        "skipped": 0,
        "failed": 0,
        "details": []
    }
    
    for customer_id in customer_ids:
        # 获取客户
        result = await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            results["skipped"] += 1
            results["details"].append({
                "customer_id": str(customer_id),
                "status": "skipped",
                "reason": "客户不存在"
            })
            continue
        
        if not customer.email:
            results["skipped"] += 1
            results["details"].append({
                "customer_id": str(customer_id),
                "customer_name": customer.name,
                "status": "skipped",
                "reason": "无邮箱地址"
            })
            continue
        
        # 发送邮件
        send_result = await email_service.send_customer_email(
            customer_id=str(customer.id),
            to_email=customer.email,
            template_id=template_id,
            variables={"customer_name": customer.name or "尊敬的客户"},
            sender_type="manual",
            sender_name="人工"
        )
        
        if send_result.get("status") == "sent":
            results["sent"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "customer_id": str(customer_id),
            "customer_name": customer.name,
            "email": customer.email,
            "status": send_result.get("status"),
            "message": send_result.get("message")
        })
    
    return {
        "success": True,
        "message": f"批量发送完成: 成功{results['sent']}，跳过{results['skipped']}，失败{results['failed']}",
        "data": results
    }


# =====================================================
# 邮件模板管理接口
# =====================================================

@router.get("/templates")
async def list_email_templates(
    template_type: Optional[str] = Query(None, description="模板类型"),
    active_only: bool = Query(True, description="仅显示启用的模板")
):
    """获取邮件模板列表"""
    templates = await email_service.get_email_templates(
        template_type=template_type,
        active_only=active_only
    )
    
    return {
        "success": True,
        "data": templates,
        "total": len(templates)
    }


@router.get("/templates/{template_id}")
async def get_email_template(template_id: str):
    """获取单个邮件模板详情"""
    template = await email_service.get_template_by_id(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return {
        "success": True,
        "data": template
    }


@router.post("/templates")
async def create_email_template(
    request: EmailTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建邮件模板"""
    try:
        result = await db.execute(
            text("""
                INSERT INTO email_templates 
                (name, template_type, subject, html_content, text_content, variables)
                VALUES (:name, :template_type, :subject, :html_content, :text_content, :variables)
                RETURNING id
            """),
            {
                "name": request.name,
                "template_type": request.template_type,
                "subject": request.subject,
                "html_content": request.html_content,
                "text_content": request.text_content,
                "variables": request.variables
            }
        )
        template_id = result.scalar()
        await db.commit()
        
        return {
            "success": True,
            "message": "模板创建成功",
            "data": {"id": str(template_id)}
        }
    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        raise HTTPException(status_code=500, detail="创建模板失败")


@router.patch("/templates/{template_id}")
async def update_email_template(
    template_id: str,
    request: EmailTemplateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新邮件模板"""
    # 构建更新字段
    update_fields = []
    params = {"template_id": template_id}
    
    if request.name is not None:
        update_fields.append("name = :name")
        params["name"] = request.name
    if request.subject is not None:
        update_fields.append("subject = :subject")
        params["subject"] = request.subject
    if request.html_content is not None:
        update_fields.append("html_content = :html_content")
        params["html_content"] = request.html_content
    if request.text_content is not None:
        update_fields.append("text_content = :text_content")
        params["text_content"] = request.text_content
    if request.is_active is not None:
        update_fields.append("is_active = :is_active")
        params["is_active"] = request.is_active
    if request.is_default is not None:
        update_fields.append("is_default = :is_default")
        params["is_default"] = request.is_default
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    
    update_fields.append("updated_at = NOW()")
    
    try:
        result = await db.execute(
            text(f"""
                UPDATE email_templates 
                SET {', '.join(update_fields)}
                WHERE id = :template_id
                RETURNING id
            """),
            params
        )
        
        if not result.scalar():
            raise HTTPException(status_code=404, detail="模板不存在")
        
        await db.commit()
        
        return {
            "success": True,
            "message": "模板更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        raise HTTPException(status_code=500, detail="更新模板失败")


@router.delete("/templates/{template_id}")
async def delete_email_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除邮件模板（软删除，设为不活跃）"""
    try:
        result = await db.execute(
            text("""
                UPDATE email_templates 
                SET is_active = false, updated_at = NOW()
                WHERE id = :template_id
                RETURNING id
            """),
            {"template_id": template_id}
        )
        
        if not result.scalar():
            raise HTTPException(status_code=404, detail="模板不存在")
        
        await db.commit()
        
        return {
            "success": True,
            "message": "模板已删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        raise HTTPException(status_code=500, detail="删除模板失败")


# =====================================================
# 邮件发送记录接口
# =====================================================

@router.get("/logs")
async def list_email_logs(
    customer_id: Optional[UUID] = Query(None, description="客户ID"),
    status: Optional[str] = Query(None, description="状态"),
    limit: int = Query(50, ge=1, le=200)
):
    """获取邮件发送记录"""
    logs = await email_service.get_email_logs(
        customer_id=str(customer_id) if customer_id else None,
        status=status,
        limit=limit
    )
    
    return {
        "success": True,
        "data": logs,
        "total": len(logs)
    }


@router.get("/logs/{customer_id}")
async def get_customer_email_logs(
    customer_id: UUID,
    limit: int = Query(20, ge=1, le=100)
):
    """获取指定客户的邮件发送记录"""
    logs = await email_service.get_email_logs(
        customer_id=str(customer_id),
        limit=limit
    )
    
    return {
        "success": True,
        "data": logs,
        "total": len(logs)
    }


# =====================================================
# 统计接口
# =====================================================

@router.get("/stats")
async def get_email_stats(
    db: AsyncSession = Depends(get_db)
):
    """获取邮件统计数据"""
    try:
        # 总体统计
        result = await db.execute(
            text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'opened' THEN 1 END) as opened,
                    COUNT(CASE WHEN DATE(created_at) = CURRENT_DATE THEN 1 END) as today
                FROM email_logs
            """)
        )
        stats = result.fetchone()
        
        # 最近7天趋势
        result = await db.execute(
            text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM email_logs
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
        )
        trends = [{"date": str(row[0]), "count": row[1]} for row in result.fetchall()]
        
        return {
            "success": True,
            "data": {
                "total": stats[0] or 0,
                "sent": stats[1] or 0,
                "failed": stats[2] or 0,
                "opened": stats[3] or 0,
                "today": stats[4] or 0,
                "trends": trends
            }
        }
    except Exception as e:
        logger.error(f"获取邮件统计失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/config-status")
async def get_email_config_status():
    """检查邮件服务配置状态"""
    return {
        "success": True,
        "data": {
            "configured": email_service.is_configured,
            "smtp_host": email_service.smtp_host if email_service.smtp_host else "未配置",
            "sender_name": email_service.sender_name
        }
    }
