"""
通知中心API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from app.models.database import AsyncSessionLocal
from sqlalchemy import text

router = APIRouter(prefix="/notifications", tags=["通知中心"])


class NotificationCreate(BaseModel):
    type: str  # high_intent, task_complete, system_alert, lead_found, video_ready
    title: str
    content: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    priority: str = "normal"  # urgent, high, normal, low
    action_url: Optional[str] = None


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    content: str
    customer_id: Optional[str]
    customer_name: Optional[str]
    is_read: bool
    priority: str
    created_at: str
    action_url: Optional[str]


@router.get("")
async def list_notifications(
    is_read: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """获取通知列表"""
    try:
        async with AsyncSessionLocal() as db:
            sql = """
                SELECT id, type, title, content, customer_id, customer_name,
                       is_read, priority, created_at, action_url
                FROM notifications
                WHERE 1=1
            """
            params = {"limit": limit, "offset": offset}
            
            if is_read is not None:
                sql += " AND is_read = :is_read"
                params["is_read"] = is_read
            
            sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            items = [
                {
                    "id": str(row[0]),
                    "type": row[1],
                    "title": row[2],
                    "content": row[3],
                    "customer_id": str(row[4]) if row[4] else None,
                    "customer_name": row[5],
                    "is_read": row[6],
                    "priority": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                    "action_url": row[9]
                }
                for row in rows
            ]
            
            # 统计未读数量
            count_result = await db.execute(
                text("SELECT COUNT(*) FROM notifications WHERE is_read = FALSE")
            )
            unread_count = count_result.scalar() or 0
            
            return {
                "items": items,
                "unread_count": unread_count,
                "total": len(items)
            }
    except Exception as e:
        logger.error(f"获取通知列表失败: {e}")
        # 返回空列表
        return {"items": [], "unread_count": 0, "total": 0}


@router.post("")
async def create_notification(data: NotificationCreate):
    """创建通知"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO notifications 
                    (type, title, content, customer_id, customer_name, priority, action_url)
                    VALUES (:type, :title, :content, :customer_id, :customer_name, :priority, :action_url)
                    RETURNING id
                """),
                {
                    "type": data.type,
                    "title": data.title,
                    "content": data.content,
                    "customer_id": data.customer_id,
                    "customer_name": data.customer_name,
                    "priority": data.priority,
                    "action_url": data.action_url
                }
            )
            notification_id = result.scalar()
            await db.commit()
            
            return {"id": str(notification_id), "message": "通知创建成功"}
    except Exception as e:
        logger.error(f"创建通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{notification_id}/read")
async def mark_as_read(notification_id: str):
    """标记通知为已读"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("UPDATE notifications SET is_read = TRUE WHERE id = :id"),
                {"id": notification_id}
            )
            await db.commit()
            return {"message": "已标记为已读"}
    except Exception as e:
        logger.error(f"标记已读失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/read-all")
async def mark_all_as_read():
    """标记所有通知为已读"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("UPDATE notifications SET is_read = TRUE"))
            await db.commit()
            return {"message": "已全部标记为已读"}
    except Exception as e:
        logger.error(f"标记全部已读失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    """删除通知"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("DELETE FROM notifications WHERE id = :id"),
                {"id": notification_id}
            )
            await db.commit()
            return {"message": "通知已删除"}
    except Exception as e:
        logger.error(f"删除通知失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
