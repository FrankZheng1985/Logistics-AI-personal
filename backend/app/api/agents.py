"""
AI员工管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from app.models import get_db, AIAgent, AgentType, AgentStatus

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
