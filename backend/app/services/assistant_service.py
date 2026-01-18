"""
小助助理服务
提供日程管理、待办事项、会议纪要的业务逻辑
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, date
from loguru import logger
from sqlalchemy import text
import json

from app.models.database import AsyncSessionLocal


class AssistantService:
    """小助助理服务类"""
    
    # ==================== 日程管理 ====================
    
    async def add_schedule(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = "normal",
        reminder_minutes: int = 15,
        reminder_day_before: bool = True
    ) -> Dict[str, Any]:
        """添加日程"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO assistant_schedules 
                        (title, description, location, start_time, end_time, priority, 
                         reminder_minutes, reminder_day_before)
                        VALUES (:title, :description, :location, :start_time, :end_time, 
                                :priority, :reminder_minutes, :reminder_day_before)
                        RETURNING id, title, start_time
                    """),
                    {
                        "title": title,
                        "description": description,
                        "location": location,
                        "start_time": start_time,
                        "end_time": end_time,
                        "priority": priority,
                        "reminder_minutes": reminder_minutes,
                        "reminder_day_before": reminder_day_before
                    }
                )
                row = result.fetchone()
                await db.commit()
                
                return {
                    "success": True,
                    "schedule_id": str(row[0]),
                    "title": row[1],
                    "start_time": row[2].isoformat()
                }
        except Exception as e:
            logger.error(f"添加日程失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_schedules_by_date(self, query_date: date) -> List[Dict[str, Any]]:
        """获取指定日期的日程"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, title, start_time, end_time, location, priority, 
                           description, is_completed
                    FROM assistant_schedules
                    WHERE DATE(start_time) = :query_date
                    ORDER BY start_time ASC
                """),
                {"query_date": query_date}
            )
            rows = result.fetchall()
        
        schedules = []
        for row in rows:
            schedules.append({
                "id": str(row[0]),
                "title": row[1],
                "start_time": row[2].isoformat() if row[2] else None,
                "end_time": row[3].isoformat() if row[3] else None,
                "location": row[4],
                "priority": row[5],
                "description": row[6],
                "is_completed": row[7]
            })
        
        return schedules
    
    async def get_schedules_by_range(
        self, 
        start_date: date, 
        end_date: date,
        include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """获取日期范围内的日程"""
        completed_filter = "" if include_completed else "AND is_completed = FALSE"
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(f"""
                    SELECT id, title, start_time, end_time, location, priority, is_completed
                    FROM assistant_schedules
                    WHERE DATE(start_time) BETWEEN :start_date AND :end_date
                    {completed_filter}
                    ORDER BY start_time ASC
                """),
                {"start_date": start_date, "end_date": end_date}
            )
            rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "title": row[1],
                "start_time": row[2].isoformat() if row[2] else None,
                "end_time": row[3].isoformat() if row[3] else None,
                "location": row[4],
                "priority": row[5],
                "is_completed": row[6]
            }
            for row in rows
        ]
    
    async def complete_schedule(self, schedule_id: str) -> bool:
        """完成日程"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE assistant_schedules
                        SET is_completed = TRUE, completed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": schedule_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"完成日程失败: {e}")
            return False
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """删除日程"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("DELETE FROM assistant_schedules WHERE id = :id"),
                    {"id": schedule_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"删除日程失败: {e}")
            return False
    
    async def get_tomorrow_schedules(self) -> List[Dict[str, Any]]:
        """获取明天的日程（用于提前一天提醒）"""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        return await self.get_schedules_by_date(tomorrow)
    
    async def get_pending_reminders(self, minutes_ahead: int = 60) -> List[Dict[str, Any]]:
        """获取即将需要提醒的日程"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, title, start_time, location, reminder_minutes
                    FROM assistant_schedules
                    WHERE is_completed = FALSE
                    AND reminder_sent = FALSE
                    AND reminder_minutes > 0
                    AND start_time BETWEEN NOW() AND NOW() + :minutes * INTERVAL '1 minute'
                """),
                {"minutes": minutes_ahead}
            )
            rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "title": row[1],
                "start_time": row[2].isoformat() if row[2] else None,
                "location": row[3],
                "reminder_minutes": row[4]
            }
            for row in rows
        ]
    
    async def mark_reminder_sent(self, schedule_id: str, day_before: bool = False):
        """标记提醒已发送"""
        field = "reminder_sent_day_before" if day_before else "reminder_sent"
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(f"UPDATE assistant_schedules SET {field} = TRUE WHERE id = :id"),
                    {"id": schedule_id}
                )
                await db.commit()
        except Exception as e:
            logger.error(f"标记提醒失败: {e}")
    
    # ==================== 待办事项 ====================
    
    async def add_todo(
        self,
        content: str,
        priority: str = "normal",
        due_date: Optional[datetime] = None,
        source_type: str = "manual",
        source_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """添加待办事项"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO assistant_todos 
                        (content, priority, due_date, source_type, source_id)
                        VALUES (:content, :priority, :due_date, :source_type, :source_id)
                        RETURNING id, content
                    """),
                    {
                        "content": content,
                        "priority": priority,
                        "due_date": due_date,
                        "source_type": source_type,
                        "source_id": source_id
                    }
                )
                row = result.fetchone()
                await db.commit()
                
                return {
                    "success": True,
                    "todo_id": str(row[0]),
                    "content": row[1]
                }
        except Exception as e:
            logger.error(f"添加待办失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_todos(
        self, 
        include_completed: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取待办列表"""
        completed_filter = "" if include_completed else "WHERE is_completed = FALSE"
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text(f"""
                    SELECT id, content, priority, due_date, is_completed, created_at
                    FROM assistant_todos
                    {completed_filter}
                    ORDER BY 
                        CASE priority 
                            WHEN 'urgent' THEN 1 
                            WHEN 'high' THEN 2 
                            WHEN 'normal' THEN 3 
                            ELSE 4 
                        END,
                        due_date ASC NULLS LAST,
                        created_at ASC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "content": row[1],
                "priority": row[2],
                "due_date": row[3].isoformat() if row[3] else None,
                "is_completed": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            }
            for row in rows
        ]
    
    async def complete_todo(self, todo_id: str) -> bool:
        """完成待办"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE assistant_todos
                        SET is_completed = TRUE, completed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": todo_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"完成待办失败: {e}")
            return False
    
    async def delete_todo(self, todo_id: str) -> bool:
        """删除待办"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("DELETE FROM assistant_todos WHERE id = :id"),
                    {"id": todo_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"删除待办失败: {e}")
            return False
    
    async def get_overdue_todos(self) -> List[Dict[str, Any]]:
        """获取逾期待办"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, content, priority, due_date
                    FROM assistant_todos
                    WHERE is_completed = FALSE
                    AND due_date < NOW()
                    ORDER BY due_date ASC
                """)
            )
            rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "content": row[1],
                "priority": row[2],
                "due_date": row[3].isoformat() if row[3] else None
            }
            for row in rows
        ]
    
    # ==================== 会议纪要 ====================
    
    async def create_meeting_record(
        self,
        title: Optional[str] = None,
        schedule_id: Optional[str] = None,
        audio_file_url: Optional[str] = None,
        audio_duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """创建会议纪要记录"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO meeting_records 
                        (title, schedule_id, audio_file_url, audio_duration_seconds, 
                         transcription_status, meeting_time)
                        VALUES (:title, :schedule_id, :audio_file_url, :audio_duration_seconds,
                                'pending', NOW())
                        RETURNING id
                    """),
                    {
                        "title": title,
                        "schedule_id": schedule_id,
                        "audio_file_url": audio_file_url,
                        "audio_duration_seconds": audio_duration_seconds
                    }
                )
                row = result.fetchone()
                await db.commit()
                
                return {
                    "success": True,
                    "meeting_id": str(row[0])
                }
        except Exception as e:
            logger.error(f"创建会议纪要失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_meeting_transcription(
        self,
        meeting_id: str,
        raw_transcription: str,
        status: str = "completed"
    ) -> bool:
        """更新会议转写结果"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE meeting_records
                        SET raw_transcription = :transcription,
                            transcription_status = :status,
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": meeting_id,
                        "transcription": raw_transcription,
                        "status": status
                    }
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"更新会议转写失败: {e}")
            return False
    
    async def update_meeting_summary(
        self,
        meeting_id: str,
        summary: str,
        content_structured: Dict[str, Any],
        action_items: List[Dict[str, Any]],
        participants: Optional[str] = None
    ) -> bool:
        """更新会议纪要摘要"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE meeting_records
                        SET summary = :summary,
                            content_structured = :content_structured,
                            action_items = :action_items,
                            participants = :participants,
                            updated_at = NOW()
                        WHERE id = :id
                    """),
                    {
                        "id": meeting_id,
                        "summary": summary,
                        "content_structured": json.dumps(content_structured, ensure_ascii=False),
                        "action_items": json.dumps(action_items, ensure_ascii=False),
                        "participants": participants
                    }
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"更新会议纪要失败: {e}")
            return False
    
    async def get_meeting_record(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """获取会议纪要详情"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, title, meeting_time, participants, summary,
                           content_structured, action_items, raw_transcription,
                           transcription_status, audio_duration_seconds
                    FROM meeting_records
                    WHERE id = :id
                """),
                {"id": meeting_id}
            )
            row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": str(row[0]),
            "title": row[1],
            "meeting_time": row[2].isoformat() if row[2] else None,
            "participants": row[3],
            "summary": row[4],
            "content_structured": row[5] if row[5] else {},
            "action_items": row[6] if row[6] else [],
            "raw_transcription": row[7],
            "transcription_status": row[8],
            "audio_duration_seconds": row[9]
        }
    
    async def get_recent_meetings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的会议纪要"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, title, meeting_time, summary, transcription_status
                    FROM meeting_records
                    ORDER BY meeting_time DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            rows = result.fetchall()
        
        return [
            {
                "id": str(row[0]),
                "title": row[1],
                "meeting_time": row[2].isoformat() if row[2] else None,
                "summary": row[3],
                "status": row[4]
            }
            for row in rows
        ]
    
    async def create_todos_from_meeting(
        self, 
        meeting_id: str, 
        action_items: List[Dict[str, Any]]
    ) -> List[str]:
        """从会议纪要创建待办事项"""
        todo_ids = []
        
        for item in action_items:
            content = item.get("task", "")
            if item.get("assignee"):
                content = f"[{item['assignee']}] {content}"
            
            # 解析截止日期
            due_date = None
            deadline = item.get("deadline", "")
            if deadline:
                # 尝试解析常见的日期表达
                # TODO: 使用更智能的日期解析
                pass
            
            result = await self.add_todo(
                content=content,
                priority=item.get("priority", "normal"),
                due_date=due_date,
                source_type="meeting",
                source_id=meeting_id
            )
            
            if result.get("success"):
                todo_ids.append(result["todo_id"])
        
        return todo_ids
    
    # ==================== 统计数据 ====================
    
    async def get_daily_stats(self) -> Dict[str, Any]:
        """获取今日统计数据"""
        today = datetime.now().date()
        
        async with AsyncSessionLocal() as db:
            # 今日日程数
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM assistant_schedules
                    WHERE DATE(start_time) = :today AND is_completed = FALSE
                """),
                {"today": today}
            )
            schedule_count = result.scalar()
            
            # 未完成待办数
            result = await db.execute(
                text("SELECT COUNT(*) FROM assistant_todos WHERE is_completed = FALSE")
            )
            todo_count = result.scalar()
            
            # 逾期待办数
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM assistant_todos
                    WHERE is_completed = FALSE AND due_date < NOW()
                """)
            )
            overdue_count = result.scalar()
        
        return {
            "date": today.isoformat(),
            "schedule_count": schedule_count,
            "todo_count": todo_count,
            "overdue_count": overdue_count
        }


# 创建单例
assistant_service = AssistantService()
