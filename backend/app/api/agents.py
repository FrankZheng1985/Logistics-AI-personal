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
            from app.agents.lead_hunter import lead_hunter_agent
            result = await lead_hunter_agent.process({"action": "smart_hunt", "max_keywords": 3, "max_results": 10})
            
        elif agent_type == AgentType.COPYWRITER:
            from app.agents.copywriter import copywriter_agent
            if task_type == "视频脚本":
                result = await copywriter_agent.process({"task_type": "script", "title": "物流服务介绍", "duration": 60})
            elif task_type == "朋友圈文案":
                result = await copywriter_agent.process({"task_type": "moments", "topic": "物流服务", "purpose": "获客引流"})
            elif task_type == "广告文案":
                result = await copywriter_agent.process({"task_type": "ad", "platform": "通用", "product": "国际物流服务"})
            else:
                result = await copywriter_agent.process({"task_type": "moments", "topic": "物流服务"})
                
        elif agent_type == AgentType.ASSET_COLLECTOR:
            from app.agents.asset_collector import asset_collector
            result = await asset_collector.process({"platforms": ["pexels", "pixabay"], "keywords": ["物流仓库", "港口集装箱"]})
            
        elif agent_type == AgentType.ANALYST:
            from app.agents.analyst import analyst_agent
            result = await analyst_agent.process({"action": "market_intel"})
            
        elif agent_type == AgentType.VIDEO_CREATOR:
            from app.agents.video_creator import video_creator_agent
            # 根据任务类型执行不同操作
            if task_type == "视频生成":
                # 使用快速模式生成演示视频
                result = await video_creator_agent.process({
                    "mode": "quick",
                    "title": "物流服务宣传视频",
                    "keywords": ["国际物流", "快速配送", "安全可靠"],
                    "video_type": "ad"
                })
            elif task_type == "脚本配合":
                # 先让小文生成脚本
                from app.agents.copywriter import copywriter_agent
                script_result = await copywriter_agent.process({
                    "task_type": "script",
                    "title": "物流服务宣传",
                    "duration": 60
                })
                result = {"message": "脚本已生成，可在视频中心查看", "script": script_result}
            elif task_type == "画面优化":
                result = {"message": "画面优化需要选择已生成的视频进行处理，请在视频中心操作", "action": "redirect", "url": "/videos"}
            elif task_type == "视频发布":
                result = {"message": "请在视频中心选择视频进行发布", "action": "redirect", "url": "/videos"}
            else:
                result = await video_creator_agent.process({
                    "mode": "quick",
                    "title": "物流服务宣传视频",
                    "keywords": ["国际物流", "快速配送"],
                    "video_type": "ad"
                })
            
        elif agent_type == AgentType.COORDINATOR:
            from app.agents.coordinator import coordinator_agent
            # 根据任务类型执行不同操作
            if task_type == "任务分配":
                result = await coordinator_agent.process({"action": "dispatch", "task_description": "系统自动调度"})
            elif task_type == "优先级调度":
                result = await coordinator_agent.process({"action": "coordinate", "workflow_type": "lead_processing"})
            elif task_type == "负载均衡":
                result = await coordinator_agent.process({"action": "monitor", "check_type": "all"})
            elif task_type == "异常处理":
                result = await coordinator_agent.process({"action": "monitor", "check_type": "all"})
            else:
                result = await coordinator_agent.process({"action": "report", "report_type": "daily"})
                
        elif agent_type == AgentType.SALES:
            from app.agents.sales_agent import sales_agent
            # 销售客服 - 不同任务类型
            if task_type == "客户接待":
                # 模拟演示对话
                result = await sales_agent.process({
                    "customer_id": "demo",
                    "message": "你好，我想咨询一下国际物流服务",
                    "context": {"user_type": "external", "demo_mode": True}
                })
            elif task_type == "需求收集":
                result = {"message": "需求收集需要在实际客户对话中进行，请在客户管理中查看待处理客户", "action": "redirect", "url": "/customers"}
            elif task_type == "报价咨询":
                result = {"message": "报价咨询需要客户提供具体货物信息，请在对话记录中处理", "action": "redirect", "url": "/conversations"}
            elif task_type == "成交促进":
                result = {"message": "成交促进需要针对具体客户操作，请在客户管理中查看高意向客户", "action": "redirect", "url": "/customers"}
            else:
                result = {"message": "小销功能需要在客户对话场景中使用，请在客户管理或对话记录中操作", "action": "redirect", "url": "/customers"}
            
        elif agent_type == AgentType.FOLLOW:
            from app.agents.follow_agent import follow_agent
            result = await follow_agent.process({"action": "check_followups"})
            
        elif agent_type == AgentType.ANALYST2:
            # 群聊情报员 - 基于监控的功能，无法手动触发实际任务
            # 但可以提供状态查询和跳转
            if task_type == "群消息监控":
                # 查询当前监控的群数量
                async with AsyncSessionLocal() as db:
                    from sqlalchemy import text
                    result_db = await db.execute(text("SELECT COUNT(*) FROM wechat_groups WHERE is_monitoring = TRUE"))
                    count = result_db.scalar() or 0
                result = {"message": f"当前正在监控 {count} 个微信群", "monitoring_count": count, "action": "redirect", "url": "/wechat-groups"}
            elif task_type == "信息提取":
                # 查询今日提取的有价值信息数量
                async with AsyncSessionLocal() as db:
                    from sqlalchemy import text
                    result_db = await db.execute(text("""
                        SELECT COUNT(*) FROM knowledge_base 
                        WHERE created_at >= CURRENT_DATE AND source = 'wechat_group'
                    """))
                    count = result_db.scalar() or 0
                result = {"message": f"今日已提取 {count} 条有价值信息", "extracted_count": count, "action": "redirect", "url": "/knowledge"}
            elif task_type == "知识库更新":
                result = {"message": "知识库更新基于群消息自动进行，请在知识库中查看最新内容", "action": "redirect", "url": "/knowledge"}
            elif task_type == "线索发现":
                # 查询今日发现的线索数量
                async with AsyncSessionLocal() as db:
                    from sqlalchemy import text
                    result_db = await db.execute(text("""
                        SELECT COUNT(*) FROM leads 
                        WHERE created_at >= CURRENT_DATE AND source = 'wechat'
                    """))
                    count = result_db.scalar() or 0
                result = {"message": f"今日从群聊发现 {count} 条潜在线索", "leads_count": count, "action": "redirect", "url": "/leads"}
            else:
                result = {"message": "小析2功能需要配合微信群监控使用，请在微信群管理中配置", "action": "redirect", "url": "/wechat-groups"}
            
        elif agent_type == AgentType.CONTENT_CREATOR:
            from app.services.content_marketing_service import content_marketing_service
            # 根据任务类型执行不同操作
            if task_type == "每日内容生成":
                result = await content_marketing_service.generate_daily_content()
            elif task_type == "多平台发布":
                result = {"message": "请在内容工作台查看待发布内容并执行发布", "action": "redirect", "url": "/content"}
            elif task_type == "内容规划":
                # 生成未来7天内容
                from datetime import date, timedelta
                results = []
                for i in range(1, 8):
                    target = date.today() + timedelta(days=i)
                    daily_result = await content_marketing_service.generate_daily_content(target)
                    results.append({"date": str(target), "result": daily_result})
                result = {"message": f"已生成未来7天内容规划", "details": results}
            elif task_type == "效果分析":
                result = {"message": "效果分析功能正在开发中，请在内容工作台查看发布状态", "action": "redirect", "url": "/content"}
            else:
                result = await content_marketing_service.generate_daily_content()
        
        elif agent_type == AgentType.EU_CUSTOMS_MONITOR:
            from app.agents.eu_customs_monitor import eu_customs_monitor_agent
            # 根据任务类型执行不同操作
            if task_type == "欧洲海关新闻采集":
                result = await eu_customs_monitor_agent.process({"action": "monitor", "max_results": 20})
            elif task_type == "反倾销政策监控":
                result = await eu_customs_monitor_agent.process({"action": "monitor", "max_results": 15})
            elif task_type == "关税调整追踪":
                result = await eu_customs_monitor_agent.process({"action": "monitor", "max_results": 15})
            elif task_type == "企业微信通知":
                # 获取统计信息并发送通知
                stats = await eu_customs_monitor_agent._get_monitor_stats()
                result = {"message": "统计信息已获取", "stats": stats}
            else:
                result = await eu_customs_monitor_agent.process({"action": "monitor", "max_results": 20})
            
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
