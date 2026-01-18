"""
小助工作台API
提供日程、待办事项、会议记录等数据的CRUD接口
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, date, timedelta
from pydantic import BaseModel
from sqlalchemy import text
from loguru import logger

from app.models.database import AsyncSessionLocal

router = APIRouter()


# ========================
# 数据模型
# ========================

class ScheduleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    priority: str = "normal"

class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None

class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "normal"
    due_date: Optional[date] = None

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    status: Optional[str] = None


# ========================
# 日程管理API
# ========================

async def _get_schedules_internal(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """获取日程列表（内部函数）"""
    try:
        async with AsyncSessionLocal() as db:
            # 构建查询条件
            conditions = []
            params = {}
            
            if date_from:
                # 将字符串转换为date对象
                from_date = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
                conditions.append("start_time::date >= :date_from")
                params["date_from"] = from_date
            if date_to:
                to_date = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
                conditions.append("start_time::date <= :date_to")
                params["date_to"] = to_date
            if status:
                # status 映射为 is_completed
                if status == "completed":
                    conditions.append("is_completed = TRUE")
                elif status == "pending":
                    conditions.append("is_completed = FALSE")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) FROM assistant_schedules WHERE {where_clause}"
            result = await db.execute(text(count_sql), params)
            total = result.scalar() or 0
            
            # 查询数据
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset
            
            data_sql = f"""
                SELECT id, title, description, location, start_time, end_time, 
                       priority, is_completed, reminder_minutes, created_at
                FROM assistant_schedules 
                WHERE {where_clause}
                ORDER BY start_time ASC
                LIMIT :limit OFFSET :offset
            """
            result = await db.execute(text(data_sql), params)
            rows = result.fetchall()
            
            schedules = []
            for row in rows:
                schedules.append({
                    "id": str(row[0]),
                    "title": row[1],
                    "description": row[2],
                    "location": row[3],
                    "start_time": row[4].isoformat() if row[4] else None,
                    "end_time": row[5].isoformat() if row[5] else None,
                    "priority": row[6],
                    "status": "completed" if row[7] else "pending",  # is_completed 映射为 status
                    "reminder_minutes": row[8],
                    "created_at": row[9].isoformat() if row[9] else None
                })
            
            return {
                "items": schedules,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
            
    except Exception as e:
        logger.error(f"获取日程列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedules")
async def get_schedules(
    date_from: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取日程列表（API路由）"""
    return await _get_schedules_internal(date_from, date_to, status, page, page_size)


@router.get("/schedules/today")
async def get_today_schedules():
    """获取今日日程"""
    today = date.today().isoformat()
    return await _get_schedules_internal(date_from=today, date_to=today)


@router.get("/schedules/upcoming")
async def get_upcoming_schedules(days: int = 7):
    """获取未来日程"""
    today = date.today()
    end_date = (today + timedelta(days=days)).isoformat()
    return await _get_schedules_internal(date_from=today.isoformat(), date_to=end_date)


@router.post("/schedules")
async def create_schedule(data: ScheduleCreate):
    """创建日程"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO assistant_schedules 
                    (title, description, location, start_time, end_time, priority)
                    VALUES (:title, :description, :location, :start_time, :end_time, :priority)
                    RETURNING id, title, start_time
                """),
                {
                    "title": data.title,
                    "description": data.description,
                    "location": data.location,
                    "start_time": data.start_time,
                    "end_time": data.end_time,
                    "priority": data.priority
                }
            )
            row = result.fetchone()
            await db.commit()
            
            return {
                "success": True,
                "id": str(row[0]),
                "title": row[1],
                "start_time": row[2].isoformat() if row[2] else None
            }
            
    except Exception as e:
        logger.error(f"创建日程失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, data: ScheduleUpdate):
    """更新日程"""
    try:
        async with AsyncSessionLocal() as db:
            # 构建更新字段
            updates = []
            params = {"id": schedule_id}
            
            if data.title is not None:
                updates.append("title = :title")
                params["title"] = data.title
            if data.description is not None:
                updates.append("description = :description")
                params["description"] = data.description
            if data.location is not None:
                updates.append("location = :location")
                params["location"] = data.location
            if data.start_time is not None:
                updates.append("start_time = :start_time")
                params["start_time"] = data.start_time
            if data.end_time is not None:
                updates.append("end_time = :end_time")
                params["end_time"] = data.end_time
            if data.priority is not None:
                updates.append("priority = :priority")
                params["priority"] = data.priority
            if data.status is not None:
                # status 映射为 is_completed
                if data.status == "completed":
                    updates.append("is_completed = TRUE")
                    updates.append("completed_at = NOW()")
                elif data.status == "pending":
                    updates.append("is_completed = FALSE")
                    updates.append("completed_at = NULL")
            
            if not updates:
                raise HTTPException(status_code=400, detail="没有要更新的字段")
            
            updates.append("updated_at = NOW()")
            
            sql = f"UPDATE assistant_schedules SET {', '.join(updates)} WHERE id = :id RETURNING id"
            result = await db.execute(text(sql), params)
            row = result.fetchone()
            await db.commit()
            
            if not row:
                raise HTTPException(status_code=404, detail="日程不存在")
            
            return {"success": True, "id": str(row[0])}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新日程失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """删除日程"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("DELETE FROM assistant_schedules WHERE id = :id RETURNING id"),
                {"id": schedule_id}
            )
            row = result.fetchone()
            await db.commit()
            
            if not row:
                raise HTTPException(status_code=404, detail="日程不存在")
            
            return {"success": True, "id": str(row[0])}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除日程失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# 待办事项API
# ========================

@router.get("/todos")
async def get_todos(
    status: Optional[str] = Query(None, description="状态筛选: pending/completed"),
    priority: Optional[str] = Query(None, description="优先级筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取待办事项列表"""
    try:
        async with AsyncSessionLocal() as db:
            # 构建查询条件
            conditions = []
            params = {}
            
            # 数据库使用 is_completed 字段
            if status:
                if status == "pending":
                    conditions.append("is_completed = FALSE")
                elif status == "completed":
                    conditions.append("is_completed = TRUE")
            if priority:
                conditions.append("priority = :priority")
                params["priority"] = priority
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) FROM assistant_todos WHERE {where_clause}"
            result = await db.execute(text(count_sql), params)
            total = result.scalar() or 0
            
            # 查询数据
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset
            
            data_sql = f"""
                SELECT id, content, priority, due_date, is_completed, completed_at, created_at
                FROM assistant_todos 
                WHERE {where_clause}
                ORDER BY 
                    is_completed ASC,
                    CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                    due_date NULLS LAST,
                    created_at DESC
                LIMIT :limit OFFSET :offset
            """
            result = await db.execute(text(data_sql), params)
            rows = result.fetchall()
            
            todos = []
            for row in rows:
                todos.append({
                    "id": str(row[0]),
                    "title": row[1],  # content 映射为 title
                    "description": None,
                    "priority": row[2],
                    "status": "completed" if row[4] else "pending",  # is_completed 映射为 status
                    "due_date": row[3].isoformat() if row[3] else None,
                    "completed_at": row[5].isoformat() if row[5] else None,
                    "created_at": row[6].isoformat() if row[6] else None
                })
            
            return {
                "items": todos,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
            
    except Exception as e:
        logger.error(f"获取待办列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/todos/pending")
async def get_pending_todos():
    """获取未完成的待办事项"""
    return await get_todos(status="pending")


@router.post("/todos")
async def create_todo(data: TodoCreate):
    """创建待办事项"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO assistant_todos 
                    (content, priority, due_date)
                    VALUES (:content, :priority, :due_date)
                    RETURNING id, content
                """),
                {
                    "content": data.title,  # title 映射为 content
                    "priority": data.priority,
                    "due_date": data.due_date
                }
            )
            row = result.fetchone()
            await db.commit()
            
            return {
                "success": True,
                "id": str(row[0]),
                "title": row[1]
            }
            
    except Exception as e:
        logger.error(f"创建待办失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/todos/{todo_id}")
async def update_todo(todo_id: str, data: TodoUpdate):
    """更新待办事项"""
    try:
        async with AsyncSessionLocal() as db:
            # 构建更新字段
            updates = []
            params = {"id": todo_id}
            
            if data.title is not None:
                updates.append("content = :content")  # title 映射为 content
                params["content"] = data.title
            if data.priority is not None:
                updates.append("priority = :priority")
                params["priority"] = data.priority
            if data.due_date is not None:
                updates.append("due_date = :due_date")
                params["due_date"] = data.due_date
            if data.status is not None:
                # status 映射为 is_completed
                if data.status == "completed":
                    updates.append("is_completed = TRUE")
                    updates.append("completed_at = NOW()")
                elif data.status == "pending":
                    updates.append("is_completed = FALSE")
                    updates.append("completed_at = NULL")
            
            if not updates:
                raise HTTPException(status_code=400, detail="没有要更新的字段")
            
            updates.append("updated_at = NOW()")
            
            sql = f"UPDATE assistant_todos SET {', '.join(updates)} WHERE id = :id RETURNING id"
            result = await db.execute(text(sql), params)
            row = result.fetchone()
            await db.commit()
            
            if not row:
                raise HTTPException(status_code=404, detail="待办不存在")
            
            return {"success": True, "id": str(row[0])}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新待办失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos/{todo_id}/complete")
async def complete_todo(todo_id: str):
    """完成待办事项"""
    return await update_todo(todo_id, TodoUpdate(status="completed"))


@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    """删除待办事项"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("DELETE FROM assistant_todos WHERE id = :id RETURNING id"),
                {"id": todo_id}
            )
            row = result.fetchone()
            await db.commit()
            
            if not row:
                raise HTTPException(status_code=404, detail="待办不存在")
            
            return {"success": True, "id": str(row[0])}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除待办失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# 会议记录API
# ========================

@router.get("/meetings")
async def get_meetings(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取会议记录列表"""
    try:
        async with AsyncSessionLocal() as db:
            conditions = []
            params = {}
            
            if date_from:
                from_date = date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
                conditions.append("meeting_time::date >= :date_from")
                params["date_from"] = from_date
            if date_to:
                to_date = date.fromisoformat(date_to) if isinstance(date_to, str) else date_to
                conditions.append("meeting_time::date <= :date_to")
                params["date_to"] = to_date
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) FROM meeting_records WHERE {where_clause}"
            result = await db.execute(text(count_sql), params)
            total = result.scalar() or 0
            
            # 查询数据
            offset = (page - 1) * page_size
            params["limit"] = page_size
            params["offset"] = offset
            
            data_sql = f"""
                SELECT id, title, meeting_time, participants, summary, 
                       action_items, transcription_status, created_at
                FROM meeting_records 
                WHERE {where_clause}
                ORDER BY meeting_time DESC
                LIMIT :limit OFFSET :offset
            """
            result = await db.execute(text(data_sql), params)
            rows = result.fetchall()
            
            meetings = []
            for row in rows:
                meetings.append({
                    "id": str(row[0]),
                    "title": row[1],
                    "meeting_date": row[2].isoformat() if row[2] else None,  # 保持API兼容
                    "participants": row[3],
                    "summary": row[4],
                    "action_items": row[5],
                    "status": row[6],  # transcription_status 映射为 status
                    "created_at": row[7].isoformat() if row[7] else None
                })
            
            return {
                "items": meetings,
                "total": total,
                "page": page,
                "page_size": page_size
            }
            
    except Exception as e:
        logger.error(f"获取会议记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    """获取会议记录详情"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, title, meeting_time, participants, raw_transcription,
                           summary, content_structured, action_items, transcription_status, created_at
                    FROM meeting_records WHERE id = :id
                """),
                {"id": meeting_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="会议记录不存在")
            
            return {
                "id": str(row[0]),
                "title": row[1],
                "meeting_date": row[2].isoformat() if row[2] else None,  # meeting_time 映射为 meeting_date
                "participants": row[3],
                "transcript": row[4],  # raw_transcription 映射为 transcript
                "summary": row[5],
                "key_points": row[6],  # content_structured 映射为 key_points
                "action_items": row[7],
                "status": row[8],  # transcription_status 映射为 status
                "created_at": row[9].isoformat() if row[9] else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会议详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# 统计数据API
# ========================

@router.get("/stats")
async def get_assistant_stats():
    """获取小助工作台统计数据"""
    try:
        async with AsyncSessionLocal() as db:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            
            # 今日日程数
            result = await db.execute(
                text("SELECT COUNT(*) FROM assistant_schedules WHERE start_time::date = :today"),
                {"today": today}
            )
            today_schedules = result.scalar() or 0
            
            # 明日日程数
            result = await db.execute(
                text("SELECT COUNT(*) FROM assistant_schedules WHERE start_time::date = :tomorrow"),
                {"tomorrow": tomorrow}
            )
            tomorrow_schedules = result.scalar() or 0
            
            # 未完成待办数
            result = await db.execute(
                text("SELECT COUNT(*) FROM assistant_todos WHERE is_completed = FALSE")
            )
            pending_todos = result.scalar() or 0
            
            # 今日完成待办数
            result = await db.execute(
                text("SELECT COUNT(*) FROM assistant_todos WHERE completed_at::date = :today"),
                {"today": today}
            )
            completed_today = result.scalar() or 0
            
            # 会议记录总数
            result = await db.execute(
                text("SELECT COUNT(*) FROM meeting_records")
            )
            total_meetings = result.scalar() or 0
            
            return {
                "today_schedules": today_schedules,
                "tomorrow_schedules": tomorrow_schedules,
                "pending_todos": pending_todos,
                "completed_today": completed_today,
                "total_meetings": total_meetings
            }
            
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
