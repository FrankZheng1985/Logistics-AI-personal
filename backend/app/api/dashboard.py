"""
数据面板API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime
from typing import Dict, Any

from app.models import get_db, Customer, IntentLevel

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
    """获取AI团队状态 - 包含当前任务信息（指挥中心用）"""
    
    # 定义所有员工信息（包含新员工小码、小知）
    all_agents_info = {
        "coordinator": {"name": "小调", "role": "调度主管"},
        "sales": {"name": "小销", "role": "销售客服"},
        "analyst": {"name": "小析", "role": "客户分析"},
        "copywriter": {"name": "小文", "role": "文案策划"},
        "video_creator": {"name": "小影", "role": "视频创作"},
        "follow": {"name": "小跟", "role": "跟进专员"},
        "lead_hunter": {"name": "小猎", "role": "线索猎手"},
        "analyst2": {"name": "小析2", "role": "群情报员"},
        "eu_customs_monitor": {"name": "小欧", "role": "海关监控"},
        "code_engineer": {"name": "小码", "role": "代码工程师"},
        "knowledge_curator": {"name": "小知", "role": "知识管理"},
    }
    
    agents = []
    
    try:
        # 1. 获取每个员工的当前任务（processing 或最新 pending）
        current_tasks = {}
        try:
            task_result = await db.execute(
                text("""
                    SELECT DISTINCT ON (agent_type) 
                        agent_type, 
                        status,
                        input_data,
                        created_at,
                        started_at
                    FROM ai_tasks 
                    WHERE status IN ('processing', 'pending')
                    ORDER BY agent_type, 
                             CASE WHEN status = 'processing' THEN 0 ELSE 1 END,
                             created_at DESC
                """)
            )
            task_rows = task_result.fetchall()
            for row in task_rows:
                agent_type = row[0]
                task_status = row[1]
                input_data = row[2] or {}
                created_at = row[3]
                started_at = row[4]
                
                # 提取任务描述
                task_desc = ""
                if isinstance(input_data, dict):
                    task_desc = input_data.get("description", "") or input_data.get("task_description", "") or input_data.get("title", "")
                
                current_tasks[agent_type] = {
                    "task": task_desc[:80] + "..." if len(task_desc) > 80 else task_desc,
                    "status": task_status,
                    "started_at": (started_at or created_at).isoformat() if (started_at or created_at) else None
                }
        except Exception as task_err:
            pass  # 任务查询失败不影响整体
        
        # 2. 获取每个员工今日完成任务数
        tasks_today = {}
        try:
            today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
            today_result = await db.execute(
                text("""
                    SELECT agent_type, COUNT(*) as cnt
                    FROM ai_tasks
                    WHERE status = 'completed' AND completed_at >= :today
                    GROUP BY agent_type
                """),
                {"today": today_start}
            )
            for row in today_result.fetchall():
                tasks_today[row[0]] = row[1]
        except:
            pass
        
        # 3. 获取每个员工最后活跃时间
        last_active = {}
        try:
            active_result = await db.execute(
                text("""
                    SELECT agent_type, MAX(COALESCE(completed_at, started_at, created_at)) as last_time
                    FROM ai_tasks
                    GROUP BY agent_type
                """)
            )
            for row in active_result.fetchall():
                if row[1]:
                    last_active[row[0]] = row[1].isoformat()
        except:
            pass
        
        # 4. 构建员工列表
        for agent_type, info in all_agents_info.items():
            current_task_info = current_tasks.get(agent_type)
            
            # 判断状态：有 processing 任务则 busy，有 pending 则 online，否则 idle
            if current_task_info:
                if current_task_info["status"] == "processing":
                    status = "busy"
                else:
                    status = "online"
                current_task = current_task_info["task"]
            else:
                status = "online"
                current_task = None
            
            agents.append({
                "name": info["name"],
                "type": agent_type,
                "role": info["role"],
                "status": status,
                "current_task": current_task,
                "tasks_today": tasks_today.get(agent_type, 0),
                "last_active": last_active.get(agent_type),
            })
        
        return {
            "agents": agents,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        # 数据库查询失败，返回基本默认数据
        for agent_type, info in all_agents_info.items():
            agents.append({
                "name": info["name"],
                "type": agent_type,
                "role": info["role"],
                "status": "online",
                "current_task": None,
                "tasks_today": 0,
                "last_active": None,
            })
        
        return {
            "agents": agents,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
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
