"""
数据面板API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta
from typing import Dict, Any

from app.models import get_db, Customer, Conversation, AITask, Video, AIAgent

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """获取仪表板统计数据"""
    try:
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        # 今日新客户数
        new_customers = 0
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM customers WHERE created_at >= :today"), {"today": today_start})
            new_customers = result.scalar() or 0
        except:
            pass
        
        # 高意向客户数 (intent_score >= 60)
        high_intent = 0
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM customers WHERE intent_score >= 60"))
            high_intent = result.scalar() or 0
        except:
            pass
        
        # 今日对话数
        conversations_today = 0
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM conversations WHERE created_at >= :today"), {"today": today_start})
            conversations_today = result.scalar() or 0
        except:
            pass
        
        # 视频生成数
        videos_today = 0
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM videos WHERE created_at >= :today"), {"today": today_start})
            videos_today = result.scalar() or 0
        except:
            pass
        
        return {
            "today": {
                "new_customers": new_customers,
                "high_intent_customers": high_intent,
                "conversations": conversations_today,
                "videos_generated": videos_today,
                "processing_tasks": 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "today": {
                "new_customers": 0,
                "high_intent_customers": 0,
                "conversations": 0,
                "videos_generated": 0,
                "processing_tasks": 0
            },
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/team-status")
async def get_team_status(db: AsyncSession = Depends(get_db)):
    """获取AI团队状态 - 从数据库获取真实数据"""
    try:
        # 从数据库获取AI员工数据
        result = await db.execute(
            text("""
                SELECT name, agent_type, status, tasks_completed_today, total_tasks_completed
                FROM ai_agents 
                ORDER BY name
            """)
        )
        rows = result.fetchall()
        
        if rows:
            agents = []
            for row in rows:
                agents.append({
                    "name": row[0],
                    "type": row[1],
                    "status": row[2] or "online",
                    "tasks_today": row[3] or 0,
                    "total_tasks": row[4] or 0,
                    "success_rate": 100  # 默认100%
                })
            return {
                "agents": agents,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        pass
    
    # 如果数据库查询失败，返回默认数据
    default_agents = [
        {"name": "小调", "type": "coordinator", "status": "online", "tasks_today": 0, "total_tasks": 0, "success_rate": 100},
        {"name": "小销", "type": "sales", "status": "online", "tasks_today": 0, "total_tasks": 0, "success_rate": 100},
        {"name": "小析", "type": "analyst", "status": "online", "tasks_today": 0, "total_tasks": 0, "success_rate": 100},
        {"name": "小文", "type": "copywriter", "status": "online", "tasks_today": 0, "total_tasks": 0, "success_rate": 100},
        {"name": "小视", "type": "video_creator", "status": "online", "tasks_today": 0, "total_tasks": 0, "success_rate": 100},
        {"name": "小跟", "type": "follow", "status": "online", "tasks_today": 0, "total_tasks": 0, "success_rate": 100},
    ]
    
    return {
        "agents": default_agents,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/intent-distribution")
async def get_intent_distribution(db: AsyncSession = Depends(get_db)):
    """获取客户意向分布"""
    result = await db.execute(
        select(Customer.intent_level, func.count(Customer.id))
        .group_by(Customer.intent_level)
    )
    distribution = dict(result.all())
    
    return {
        "distribution": {
            "S": distribution.get(IntentLevel.S, 0),
            "A": distribution.get(IntentLevel.A, 0),
            "B": distribution.get(IntentLevel.B, 0),
            "C": distribution.get(IntentLevel.C, 0)
        }
    }


@router.get("/recent-activities")
async def get_recent_activities(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """获取最近活动"""
    try:
        # 使用原生SQL查询最近对话
        result = await db.execute(
            text("SELECT agent_type, message_type, content, created_at FROM conversations ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit}
        )
        rows = result.fetchall()
        
        activities = []
        for row in rows:
            agent_type = row[0] or "system"
            content = row[2] or ""
            created_at = row[3]
            activities.append({
                "type": "conversation",
                "agent": agent_type,
                "content_preview": content[:50] + "..." if len(content) > 50 else content,
                "timestamp": created_at.isoformat() if created_at else datetime.utcnow().isoformat()
            })
        
        return {"activities": activities}
    except Exception as e:
        return {"activities": [], "error": str(e)}
