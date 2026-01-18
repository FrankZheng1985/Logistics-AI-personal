"""
AI员工管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from uuid import UUID
from datetime import datetime
from loguru import logger

from app.models import get_db, AIAgent, AgentType, AgentStatus
from app.models.database import AsyncSessionLocal

router = APIRouter()


@router.get("")
async def list_agents(db: AsyncSession = Depends(get_db)):
    """获取所有AI员工"""
    result = await db.execute(select(AIAgent))
    agents = result.scalars().all()
    
    return {
        "agents": [
            {
                "id": str(agent.id),
                "name": agent.name,
                "type": agent.agent_type.value,
                "description": agent.description,
                "status": agent.status.value,
                "tasks_today": agent.tasks_completed_today,
                "total_tasks": agent.total_tasks_completed,
                "current_task_id": str(agent.current_task_id) if agent.current_task_id else None
            }
            for agent in agents
        ]
    }


@router.get("/{agent_type}")
async def get_agent(
    agent_type: AgentType,
    db: AsyncSession = Depends(get_db)
):
    """获取指定类型的AI员工"""
    result = await db.execute(
        select(AIAgent).where(AIAgent.agent_type == agent_type)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="AI员工不存在")
    
    return {
        "id": str(agent.id),
        "name": agent.name,
        "type": agent.agent_type.value,
        "description": agent.description,
        "status": agent.status.value,
        "tasks_today": agent.tasks_completed_today,
        "total_tasks": agent.total_tasks_completed,
        "config": agent.config
    }


@router.post("/{agent_type}/config")
async def update_agent_config(
    agent_type: AgentType,
    config: dict,
    db: AsyncSession = Depends(get_db)
):
    """更新AI员工配置"""
    result = await db.execute(
        select(AIAgent).where(AIAgent.agent_type == agent_type)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="AI员工不存在")
    
    # 合并配置
    agent.config = {**agent.config, **config}
    await db.commit()
    
    return {
        "agent": agent.name,
        "config": agent.config,
        "message": "配置已更新"
    }


@router.post("/{agent_type}/reset-daily")
async def reset_daily_stats(
    agent_type: AgentType,
    db: AsyncSession = Depends(get_db)
):
    """重置AI员工每日统计"""
    result = await db.execute(
        select(AIAgent).where(AIAgent.agent_type == agent_type)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="AI员工不存在")
    
    agent.tasks_completed_today = 0
    await db.commit()
    
    return {
        "agent": agent.name,
        "message": "每日统计已重置"
    }


@router.put("/{agent_type}/status")
async def update_agent_status(
    agent_type: AgentType,
    status: AgentStatus,
    db: AsyncSession = Depends(get_db)
):
    """更新AI员工状态"""
    result = await db.execute(
        select(AIAgent).where(AIAgent.agent_type == agent_type)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="AI员工不存在")
    
    old_status = agent.status
    agent.status = status
    await db.commit()
    
    return {
        "agent": agent.name,
        "old_status": old_status.value,
        "new_status": status.value,
        "message": f"状态已更新为 {status.value}"
    }


@router.post("/by-name/{agent_name}/status")
async def update_agent_status_by_name(
    agent_name: str,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    """通过名称更新AI员工状态"""
    result = await db.execute(
        select(AIAgent).where(AIAgent.name == agent_name)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"AI员工 {agent_name} 不存在")
    
    try:
        new_status = AgentStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
    
    old_status = agent.status
    agent.status = new_status
    await db.commit()
    
    return {
        "agent": agent.name,
        "old_status": old_status.value,
        "new_status": new_status.value,
        "message": f"状态已更新为 {new_status.value}"
    }


@router.post("/{agent_type}/trigger")
async def trigger_agent_task(
    agent_type: AgentType,
    request_body: dict = None
):
    """手动触发AI员工任务
    
    Args:
        agent_type: 员工类型
        request_body: {"task_type": "任务类型"}
    """
    task_type = request_body.get("task_type", "default") if request_body else "default"
    
    try:
        # 根据不同员工类型触发不同任务
        if agent_type == AgentType.LEAD_HUNTER:
            from app.agents.lead_hunter import lead_hunter
            result = await lead_hunter.process({"action": "smart_hunt", "max_keywords": 3, "max_results": 10})
            
        elif agent_type == AgentType.COPYWRITER:
            from app.agents.copywriter import copywriter
            if task_type == "视频脚本":
                result = await copywriter.process({"task_type": "script", "title": "物流服务介绍", "duration": 60})
            elif task_type == "朋友圈文案":
                result = await copywriter.process({"task_type": "moments", "topic": "物流服务", "purpose": "获客引流"})
            elif task_type == "广告文案":
                result = await copywriter.process({"task_type": "ad", "platform": "通用", "product": "国际物流服务"})
            else:
                result = await copywriter.process({"task_type": "moments", "topic": "物流服务"})
                
        elif agent_type == AgentType.ASSET_COLLECTOR:
            from app.agents.asset_collector import asset_collector
            result = await asset_collector.process({"platforms": ["pexels", "pixabay"], "keywords": ["物流仓库", "港口集装箱"]})
            
        elif agent_type == AgentType.ANALYST:
            from app.agents.analyst import analyst
            result = await analyst.process({"action": "market_intel"})
            
        elif agent_type == AgentType.VIDEO_CREATOR:
            # 视频创作需要先有脚本
            result = {"message": "请先通过小文创建视频脚本，再触发视频生成"}
            
        else:
            result = {"message": f"{agent_type.value} 暂不支持手动触发"}
        
        return {
            "success": True,
            "agent_type": agent_type.value,
            "task_type": task_type,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"触发任务失败: {e}")
        return {
            "success": False,
            "agent_type": agent_type.value,
            "task_type": task_type,
            "error": str(e)
        }


@router.get("/{agent_type}/logs")
async def get_agent_logs(
    agent_type: AgentType,
    limit: int = Query(20, ge=1, le=100)
):
    """获取AI员工工作日志"""
    try:
        async with AsyncSessionLocal() as db:
            # 先获取agent ID
            result = await db.execute(
                text("SELECT id FROM ai_agents WHERE agent_type = :agent_type"),
                {"agent_type": agent_type.value}
            )
            agent_row = result.fetchone()
            
            if not agent_row:
                return {"logs": []}
            
            agent_id = agent_row[0]
            
            # 获取工作日志
            result = await db.execute(
                text("""
                    SELECT id, task_type, status, started_at, completed_at, 
                           duration_ms, input_data, output_data, error_message
                    FROM work_logs
                    WHERE agent_id = :agent_id
                    ORDER BY started_at DESC
                    LIMIT :limit
                """),
                {"agent_id": agent_id, "limit": limit}
            )
            rows = result.fetchall()
            
            logs = [
                {
                    "id": str(row[0]),
                    "task_type": row[1],
                    "status": row[2],
                    "started_at": row[3].isoformat() if row[3] else None,
                    "completed_at": row[4].isoformat() if row[4] else None,
                    "duration_ms": row[5],
                    "input_data": row[6],
                    "output_data": row[7],
                    "error_message": row[8]
                }
                for row in rows
            ]
            
            return {"logs": logs}
    except Exception as e:
        logger.error(f"获取工作日志失败: {e}")
        return {"logs": []}
