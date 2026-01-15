"""
微信群监控API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from app.models.database import AsyncSessionLocal
from sqlalchemy import text

router = APIRouter(prefix="/wechat-groups", tags=["微信群监控"])


class WechatGroupCreate(BaseModel):
    name: str
    wechat_group_id: Optional[str] = None


class WechatGroupResponse(BaseModel):
    id: str
    name: str
    member_count: int
    is_monitoring: bool
    messages_today: int
    leads_found: int
    intel_count: int
    last_activity: Optional[str]


@router.get("")
async def list_groups():
    """获取微信群列表"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, name, member_count, is_monitoring, 
                           messages_today, leads_found, intel_count, last_activity_at
                    FROM wechat_groups
                    ORDER BY is_monitoring DESC, last_activity_at DESC NULLS LAST
                """)
            )
            rows = result.fetchall()
            
            groups = []
            for row in rows:
                last_activity = None
                if row[7]:
                    diff = datetime.now() - row[7].replace(tzinfo=None)
                    if diff.total_seconds() < 60:
                        last_activity = "刚刚"
                    elif diff.total_seconds() < 3600:
                        last_activity = f"{int(diff.total_seconds() / 60)}分钟前"
                    elif diff.total_seconds() < 86400:
                        last_activity = f"{int(diff.total_seconds() / 3600)}小时前"
                    else:
                        last_activity = f"{int(diff.total_seconds() / 86400)}天前"
                elif not row[3]:  # 未监控
                    last_activity = "已暂停"
                
                groups.append({
                    "id": str(row[0]),
                    "name": row[1],
                    "member_count": row[2] or 0,
                    "is_monitoring": row[3],
                    "messages_today": row[4] or 0,
                    "leads_found": row[5] or 0,
                    "intel_count": row[6] or 0,
                    "last_activity": last_activity
                })
            
            return {"groups": groups}
    except Exception as e:
        logger.error(f"获取微信群列表失败: {e}")
        return {"groups": []}


@router.get("/messages")
async def list_group_messages(
    group_id: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """获取群消息列表"""
    try:
        async with AsyncSessionLocal() as db:
            sql = """
                SELECT gm.id, wg.name as group_name, gm.sender_name, gm.content,
                       gm.category, gm.created_at
                FROM group_messages gm
                JOIN wechat_groups wg ON gm.group_id = wg.id
                WHERE 1=1
            """
            params = {"limit": limit}
            
            if group_id:
                sql += " AND gm.group_id = :group_id"
                params["group_id"] = group_id
            
            if category:
                sql += " AND gm.category = :category"
                params["category"] = category
            
            sql += " ORDER BY gm.created_at DESC LIMIT :limit"
            
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            messages = [
                {
                    "id": str(row[0]),
                    "group_name": row[1],
                    "sender": row[2],
                    "content": row[3],
                    "category": row[4] or "irrelevant",
                    "time": row[5].strftime("%H:%M") if row[5] else ""
                }
                for row in rows
            ]
            
            return {"messages": messages}
    except Exception as e:
        logger.error(f"获取群消息失败: {e}")
        return {"messages": []}


@router.get("/stats")
async def get_stats():
    """获取统计数据"""
    try:
        async with AsyncSessionLocal() as db:
            # 监控中的群数
            result = await db.execute(
                text("SELECT COUNT(*) FROM wechat_groups WHERE is_monitoring = TRUE")
            )
            active_groups = result.scalar() or 0
            
            # 总群数
            result = await db.execute(text("SELECT COUNT(*) FROM wechat_groups"))
            total_groups = result.scalar() or 0
            
            # 今日线索
            result = await db.execute(
                text("SELECT COALESCE(SUM(leads_found), 0) FROM wechat_groups")
            )
            total_leads = result.scalar() or 0
            
            # 今日情报
            result = await db.execute(
                text("SELECT COALESCE(SUM(intel_count), 0) FROM wechat_groups")
            )
            total_intel = result.scalar() or 0
            
            # 今日消息
            result = await db.execute(
                text("SELECT COALESCE(SUM(messages_today), 0) FROM wechat_groups")
            )
            total_messages = result.scalar() or 0
            
            return {
                "active_groups": active_groups,
                "total_groups": total_groups,
                "total_leads": total_leads,
                "total_intel": total_intel,
                "total_messages": total_messages
            }
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return {
            "active_groups": 0,
            "total_groups": 0,
            "total_leads": 0,
            "total_intel": 0,
            "total_messages": 0
        }


@router.post("")
async def create_group(data: WechatGroupCreate):
    """添加微信群"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO wechat_groups (name, wechat_group_id, is_monitoring)
                    VALUES (:name, :wechat_group_id, TRUE)
                    RETURNING id
                """),
                {"name": data.name, "wechat_group_id": data.wechat_group_id}
            )
            group_id = result.scalar()
            await db.commit()
            
            return {"id": str(group_id), "message": "群组添加成功"}
    except Exception as e:
        logger.error(f"添加群组失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{group_id}/toggle-monitoring")
async def toggle_monitoring(group_id: str):
    """切换监控状态"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT is_monitoring FROM wechat_groups WHERE id = :id"),
                {"id": group_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="群组不存在")
            
            new_status = not row[0]
            await db.execute(
                text("UPDATE wechat_groups SET is_monitoring = :status WHERE id = :id"),
                {"id": group_id, "status": new_status}
            )
            await db.commit()
            
            return {"message": f"监控已{'开启' if new_status else '暂停'}", "is_monitoring": new_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换监控状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
