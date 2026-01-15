"""
营销序列API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uuid

from app.models import get_db

router = APIRouter()


# 请求/响应模型
class SequenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str  # first_inquiry, no_reply_3d, inactive_30d, manual
    trigger_condition: Optional[Dict] = {}


class SequenceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_condition: Optional[Dict] = None
    status: Optional[str] = None


class EmailCreate(BaseModel):
    subject: str
    content: str
    delay_days: int = 0


@router.get("")
async def get_sequences(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取营销序列列表"""
    try:
        query = """
            SELECT 
                id, name, description, trigger_type, trigger_condition,
                status, email_count, enrolled_count, converted_count,
                created_at, updated_at
            FROM marketing_sequences
        """
        params = {}
        
        if status:
            query += " WHERE status = :status"
            params["status"] = status
            
        query += " ORDER BY created_at DESC"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        items = []
        for row in rows:
            enrolled = row[7] or 0
            converted = row[8] or 0
            conversion_rate = (converted / enrolled * 100) if enrolled > 0 else 0
            
            items.append({
                "id": str(row[0]),
                "name": row[1],
                "description": row[2],
                "trigger_type": row[3],
                "trigger_condition": row[4] or {},
                "status": row[5],
                "email_count": row[6] or 0,
                "enrolled_count": enrolled,
                "converted_count": converted,
                "conversion_rate": round(conversion_rate, 1),
                "created_at": row[9].isoformat() if row[9] else None,
                "updated_at": row[10].isoformat() if row[10] else None
            })
        
        # 统计数据
        total = len(items)
        active_count = len([i for i in items if i["status"] == "active"])
        total_enrolled = sum(i["enrolled_count"] for i in items)
        avg_conversion = (
            sum(i["conversion_rate"] for i in items if i["enrolled_count"] > 0) / 
            len([i for i in items if i["enrolled_count"] > 0])
        ) if any(i["enrolled_count"] > 0 for i in items) else 0
        
        return {
            "items": items,
            "total": total,
            "stats": {
                "total": total,
                "active": active_count,
                "total_enrolled": total_enrolled,
                "avg_conversion_rate": round(avg_conversion, 1)
            }
        }
    except Exception as e:
        # 如果表不存在，返回空数据
        return {
            "items": [],
            "total": 0,
            "stats": {
                "total": 0,
                "active": 0,
                "total_enrolled": 0,
                "avg_conversion_rate": 0
            },
            "error": str(e)
        }


@router.get("/{sequence_id}")
async def get_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取单个营销序列详情"""
    try:
        result = await db.execute(
            text("""
                SELECT 
                    id, name, description, trigger_type, trigger_condition,
                    status, email_count, enrolled_count, converted_count,
                    created_at, updated_at
                FROM marketing_sequences
                WHERE id = :id
            """),
            {"id": sequence_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="序列不存在")
        
        enrolled = row[7] or 0
        converted = row[8] or 0
        conversion_rate = (converted / enrolled * 100) if enrolled > 0 else 0
        
        # 获取邮件列表
        emails_result = await db.execute(
            text("""
                SELECT id, order_index, subject, content, delay_days, created_at
                FROM sequence_emails
                WHERE sequence_id = :sequence_id
                ORDER BY order_index
            """),
            {"sequence_id": sequence_id}
        )
        emails = []
        for email_row in emails_result.fetchall():
            emails.append({
                "id": str(email_row[0]),
                "order_index": email_row[1],
                "subject": email_row[2],
                "content": email_row[3],
                "delay_days": email_row[4],
                "created_at": email_row[5].isoformat() if email_row[5] else None
            })
        
        return {
            "id": str(row[0]),
            "name": row[1],
            "description": row[2],
            "trigger_type": row[3],
            "trigger_condition": row[4] or {},
            "status": row[5],
            "email_count": row[6] or 0,
            "enrolled_count": enrolled,
            "converted_count": converted,
            "conversion_rate": round(conversion_rate, 1),
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
            "emails": emails
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_sequence(
    data: SequenceCreate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """创建营销序列"""
    try:
        sequence_id = str(uuid.uuid4())
        
        await db.execute(
            text("""
                INSERT INTO marketing_sequences (id, name, description, trigger_type, trigger_condition, status)
                VALUES (:id, :name, :description, :trigger_type, :trigger_condition, 'draft')
            """),
            {
                "id": sequence_id,
                "name": data.name,
                "description": data.description,
                "trigger_type": data.trigger_type,
                "trigger_condition": str(data.trigger_condition) if data.trigger_condition else '{}'
            }
        )
        await db.commit()
        
        return {
            "id": sequence_id,
            "message": "序列创建成功"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{sequence_id}")
async def update_sequence(
    sequence_id: str,
    data: SequenceUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """更新营销序列"""
    try:
        updates = []
        params = {"id": sequence_id}
        
        if data.name is not None:
            updates.append("name = :name")
            params["name"] = data.name
        if data.description is not None:
            updates.append("description = :description")
            params["description"] = data.description
        if data.trigger_type is not None:
            updates.append("trigger_type = :trigger_type")
            params["trigger_type"] = data.trigger_type
        if data.trigger_condition is not None:
            updates.append("trigger_condition = :trigger_condition")
            params["trigger_condition"] = str(data.trigger_condition)
        if data.status is not None:
            updates.append("status = :status")
            params["status"] = data.status
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE marketing_sequences SET {', '.join(updates)} WHERE id = :id"
            await db.execute(text(query), params)
            await db.commit()
        
        return {"message": "更新成功"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sequence_id}/toggle")
async def toggle_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """切换序列状态（暂停/启动）"""
    try:
        # 获取当前状态
        result = await db.execute(
            text("SELECT status FROM marketing_sequences WHERE id = :id"),
            {"id": sequence_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="序列不存在")
        
        current_status = row[0]
        new_status = "paused" if current_status == "active" else "active"
        
        await db.execute(
            text("""
                UPDATE marketing_sequences 
                SET status = :status, updated_at = CURRENT_TIMESTAMP 
                WHERE id = :id
            """),
            {"id": sequence_id, "status": new_status}
        )
        await db.commit()
        
        return {
            "message": "状态已更新",
            "status": new_status
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{sequence_id}")
async def delete_sequence(
    sequence_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """删除营销序列"""
    try:
        await db.execute(
            text("DELETE FROM marketing_sequences WHERE id = :id"),
            {"id": sequence_id}
        )
        await db.commit()
        
        return {"message": "序列已删除"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{sequence_id}/emails")
async def add_email_to_sequence(
    sequence_id: str,
    data: EmailCreate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """添加邮件到序列"""
    try:
        # 获取当前邮件数量
        result = await db.execute(
            text("SELECT COALESCE(MAX(order_index), 0) + 1 FROM sequence_emails WHERE sequence_id = :sequence_id"),
            {"sequence_id": sequence_id}
        )
        next_order = result.scalar() or 1
        
        email_id = str(uuid.uuid4())
        
        await db.execute(
            text("""
                INSERT INTO sequence_emails (id, sequence_id, order_index, subject, content, delay_days)
                VALUES (:id, :sequence_id, :order_index, :subject, :content, :delay_days)
            """),
            {
                "id": email_id,
                "sequence_id": sequence_id,
                "order_index": next_order,
                "subject": data.subject,
                "content": data.content,
                "delay_days": data.delay_days
            }
        )
        
        # 更新序列邮件数量
        await db.execute(
            text("""
                UPDATE marketing_sequences 
                SET email_count = (SELECT COUNT(*) FROM sequence_emails WHERE sequence_id = :sequence_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :sequence_id
            """),
            {"sequence_id": sequence_id}
        )
        
        await db.commit()
        
        return {
            "id": email_id,
            "message": "邮件添加成功"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
