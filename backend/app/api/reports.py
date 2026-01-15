"""
数据报表API
提供AI员工工作数据、业务统计、转化漏斗等报表
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text
from loguru import logger

from app.models.database import async_session_maker

router = APIRouter(prefix="/reports", tags=["报表"])


@router.get("/overview")
async def get_overview_report(
    days: int = Query(7, ge=1, le=90, description="统计天数")
):
    """
    获取概览报表
    包括：线索、客户、对话、视频等核心指标
    """
    try:
        async with async_session_maker() as db:
            # 线索统计
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day') as today,
                        COUNT(*) FILTER (WHERE status = 'converted') as converted
                    FROM leads
                    WHERE created_at > NOW() - INTERVAL :days
                """),
                {"days": f"{days} days"}
            )
            leads_stats = result.fetchone()
            
            # 客户统计
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 day') as today,
                        COUNT(*) FILTER (WHERE intent_level IN ('S', 'A')) as high_intent
                    FROM customers
                    WHERE created_at > NOW() - INTERVAL :days
                """),
                {"days": f"{days} days"}
            )
            customer_stats = result.fetchone()
            
            # 对话统计
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE message_type = 'inbound') as inbound,
                        COUNT(*) FILTER (WHERE message_type = 'outbound') as outbound
                    FROM conversations
                    WHERE created_at > NOW() - INTERVAL :days
                """),
                {"days": f"{days} days"}
            )
            conversation_stats = result.fetchone()
            
            # 视频统计
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'success') as success
                    FROM videos
                    WHERE created_at > NOW() - INTERVAL :days
                """),
                {"days": f"{days} days"}
            )
            video_stats = result.fetchone()
            
            return {
                "period_days": days,
                "leads": {
                    "total": leads_stats[0] if leads_stats else 0,
                    "today": leads_stats[1] if leads_stats else 0,
                    "converted": leads_stats[2] if leads_stats else 0,
                    "conversion_rate": round(leads_stats[2] / leads_stats[0] * 100, 1) if leads_stats and leads_stats[0] > 0 else 0
                },
                "customers": {
                    "total": customer_stats[0] if customer_stats else 0,
                    "today": customer_stats[1] if customer_stats else 0,
                    "high_intent": customer_stats[2] if customer_stats else 0
                },
                "conversations": {
                    "total": conversation_stats[0] if conversation_stats else 0,
                    "inbound": conversation_stats[1] if conversation_stats else 0,
                    "outbound": conversation_stats[2] if conversation_stats else 0
                },
                "videos": {
                    "total": video_stats[0] if video_stats else 0,
                    "success": video_stats[1] if video_stats else 0
                }
            }
    except Exception as e:
        logger.error(f"获取概览报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_agents_report(
    days: int = Query(7, ge=1, le=90)
):
    """
    获取AI员工工作报表
    """
    try:
        async with async_session_maker() as db:
            # 员工基本统计
            result = await db.execute(
                text("""
                    SELECT 
                        agent_type,
                        name,
                        status,
                        tasks_completed_today,
                        tasks_completed_total,
                        success_rate,
                        last_active_at
                    FROM ai_agents
                    ORDER BY tasks_completed_total DESC
                """)
            )
            agents = result.fetchall()
            
            # 工作日志统计
            result = await db.execute(
                text("""
                    SELECT 
                        agent_type,
                        COUNT(*) as task_count,
                        COUNT(*) FILTER (WHERE status = 'success') as success_count,
                        AVG(duration_ms) as avg_duration
                    FROM agent_work_logs
                    WHERE created_at > NOW() - INTERVAL :days
                    GROUP BY agent_type
                """),
                {"days": f"{days} days"}
            )
            work_stats = {row[0]: {
                "task_count": row[1],
                "success_count": row[2],
                "avg_duration_ms": round(row[3]) if row[3] else 0
            } for row in result.fetchall()}
            
            agent_list = []
            for agent in agents:
                agent_type = agent[0]
                stats = work_stats.get(agent_type, {})
                
                agent_list.append({
                    "agent_type": agent_type,
                    "name": agent[1],
                    "status": agent[2],
                    "tasks_today": agent[3] or 0,
                    "tasks_total": agent[4] or 0,
                    "success_rate": float(agent[5]) if agent[5] else 0,
                    "last_active": agent[6].isoformat() if agent[6] else None,
                    "period_stats": stats
                })
            
            return {
                "period_days": days,
                "agents": agent_list
            }
    except Exception as e:
        logger.error(f"获取员工报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funnel")
async def get_conversion_funnel(
    days: int = Query(30, ge=1, le=90)
):
    """
    获取转化漏斗数据
    """
    try:
        async with async_session_maker() as db:
            # 漏斗各阶段数据
            result = await db.execute(
                text("""
                    SELECT 
                        'leads' as stage,
                        COUNT(*) as count
                    FROM leads
                    WHERE created_at > NOW() - INTERVAL :days
                    
                    UNION ALL
                    
                    SELECT 
                        'qualified' as stage,
                        COUNT(*) as count
                    FROM leads
                    WHERE created_at > NOW() - INTERVAL :days
                    AND quality_score >= 60
                    
                    UNION ALL
                    
                    SELECT 
                        'contacted' as stage,
                        COUNT(DISTINCT customer_id) as count
                    FROM conversations
                    WHERE created_at > NOW() - INTERVAL :days
                    AND message_type = 'outbound'
                    
                    UNION ALL
                    
                    SELECT 
                        'high_intent' as stage,
                        COUNT(*) as count
                    FROM customers
                    WHERE created_at > NOW() - INTERVAL :days
                    AND intent_level IN ('S', 'A')
                    
                    UNION ALL
                    
                    SELECT 
                        'converted' as stage,
                        COUNT(*) as count
                    FROM leads
                    WHERE created_at > NOW() - INTERVAL :days
                    AND status = 'converted'
                """),
                {"days": f"{days} days"}
            )
            funnel_data = {row[0]: row[1] for row in result.fetchall()}
            
            stages = [
                {"stage": "leads", "name": "原始线索", "count": funnel_data.get("leads", 0)},
                {"stage": "qualified", "name": "合格线索", "count": funnel_data.get("qualified", 0)},
                {"stage": "contacted", "name": "已联系", "count": funnel_data.get("contacted", 0)},
                {"stage": "high_intent", "name": "高意向", "count": funnel_data.get("high_intent", 0)},
                {"stage": "converted", "name": "已成交", "count": funnel_data.get("converted", 0)}
            ]
            
            # 计算转化率
            for i, stage in enumerate(stages):
                if i > 0 and stages[i-1]["count"] > 0:
                    stage["conversion_rate"] = round(stage["count"] / stages[i-1]["count"] * 100, 1)
                else:
                    stage["conversion_rate"] = 0
            
            return {
                "period_days": days,
                "funnel": stages
            }
    except Exception as e:
        logger.error(f"获取转化漏斗失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels")
async def get_channel_report(
    days: int = Query(30, ge=1, le=90)
):
    """
    获取渠道分析报表
    """
    try:
        async with async_session_maker() as db:
            # 各渠道线索量
            result = await db.execute(
                text("""
                    SELECT 
                        COALESCE(source_channel, 'unknown') as channel,
                        COUNT(*) as lead_count,
                        COUNT(*) FILTER (WHERE status = 'converted') as converted_count,
                        AVG(quality_score) as avg_quality
                    FROM leads
                    WHERE created_at > NOW() - INTERVAL :days
                    GROUP BY source_channel
                    ORDER BY lead_count DESC
                """),
                {"days": f"{days} days"}
            )
            channel_stats = result.fetchall()
            
            channel_names = {
                "lead_hunter": "小猎(搜索)",
                "copywriter": "小文(内容)",
                "video_creator": "小视(视频)",
                "wechat": "企业微信",
                "webchat": "网站客服",
                "wechat_group": "微信群",
                "unknown": "未知渠道"
            }
            
            channels = []
            for row in channel_stats:
                channel = row[0]
                lead_count = row[1]
                converted = row[2]
                
                channels.append({
                    "channel": channel,
                    "channel_name": channel_names.get(channel, channel),
                    "lead_count": lead_count,
                    "converted_count": converted,
                    "conversion_rate": round(converted / lead_count * 100, 1) if lead_count > 0 else 0,
                    "avg_quality_score": round(row[3], 1) if row[3] else 0
                })
            
            return {
                "period_days": days,
                "channels": channels
            }
    except Exception as e:
        logger.error(f"获取渠道报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_trend_report(
    days: int = Query(30, ge=1, le=90),
    metric: str = Query("leads", description="指标: leads/customers/conversations")
):
    """
    获取趋势数据
    """
    try:
        async with async_session_maker() as db:
            table_map = {
                "leads": "leads",
                "customers": "customers",
                "conversations": "conversations"
            }
            
            table = table_map.get(metric, "leads")
            
            result = await db.execute(
                text(f"""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as count
                    FROM {table}
                    WHERE created_at > NOW() - INTERVAL :days
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """),
                {"days": f"{days} days"}
            )
            
            trend_data = [
                {
                    "date": row[0].strftime("%Y-%m-%d"),
                    "count": row[1]
                }
                for row in result.fetchall()
            ]
            
            return {
                "metric": metric,
                "period_days": days,
                "trend": trend_data
            }
    except Exception as e:
        logger.error(f"获取趋势数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-intel")
async def get_market_intel_report(
    days: int = Query(7, ge=1, le=30)
):
    """
    获取市场情报报表
    """
    try:
        async with async_session_maker() as db:
            # 情报统计
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE is_urgent = true) as urgent_count,
                        COUNT(*) FILTER (WHERE intel_type = 'news') as news_count,
                        COUNT(*) FILTER (WHERE intel_type = 'policy') as policy_count,
                        COUNT(*) FILTER (WHERE intel_type = 'price') as price_count
                    FROM market_intel
                    WHERE created_at > NOW() - INTERVAL :days
                """),
                {"days": f"{days} days"}
            )
            stats = result.fetchone()
            
            # 最新情报
            result = await db.execute(
                text("""
                    SELECT title, intel_type, is_urgent, url, created_at
                    FROM market_intel
                    WHERE created_at > NOW() - INTERVAL :days
                    ORDER BY created_at DESC
                    LIMIT 20
                """),
                {"days": f"{days} days"}
            )
            latest_intel = result.fetchall()
            
            return {
                "period_days": days,
                "statistics": {
                    "total": stats[0] if stats else 0,
                    "urgent": stats[1] if stats else 0,
                    "news": stats[2] if stats else 0,
                    "policy": stats[3] if stats else 0,
                    "price": stats[4] if stats else 0
                },
                "latest": [
                    {
                        "title": row[0],
                        "type": row[1],
                        "is_urgent": row[2],
                        "url": row[3],
                        "created_at": row[4].isoformat() if row[4] else None
                    }
                    for row in latest_intel
                ]
            }
    except Exception as e:
        logger.error(f"获取市场情报报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily/latest")
async def get_latest_daily_report():
    """
    获取最新的每日报告
    """
    try:
        from app.services.report_generator import report_generator
        
        report = await report_generator.get_latest_report("daily")
        
        if not report:
            # 如果没有报告，立即生成一份
            report = await report_generator.generate_daily_report()
        
        return report
    except Exception as e:
        logger.error(f"获取最新报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily/{date}")
async def get_daily_report_by_date(date: str):
    """
    根据日期获取每日报告
    日期格式: YYYY-MM-DD
    """
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                text("""
                    SELECT report_date, agent_stats, system_health, 
                           business_metrics, summary, highlights, issues,
                           recommendations, generation_time_ms, created_at
                    FROM daily_reports
                    WHERE report_date = :date AND report_type = 'daily'
                    LIMIT 1
                """),
                {"date": date}
            )
            
            row = result.fetchone()
            if row:
                return {
                    "report_date": str(row[0]),
                    "report_type": "daily",
                    "agent_stats": row[1],
                    "system_health": row[2],
                    "business_metrics": row[3],
                    "summary": row[4],
                    "highlights": row[5],
                    "issues": row[6],
                    "recommendations": row[7],
                    "generation_time_ms": row[8],
                    "created_at": row[9].isoformat() if row[9] else None
                }
            
            raise HTTPException(status_code=404, detail="报告不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge")
async def get_knowledge_report():
    """
    获取知识库报表
    """
    try:
        from app.services.knowledge_base import knowledge_base
        return await knowledge_base.get_statistics()
    except Exception as e:
        logger.error(f"获取知识库报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler")
async def get_scheduler_report():
    """
    获取定时任务报表
    """
    try:
        from app.scheduler import get_jobs
        
        jobs = get_jobs()
        
        return {
            "total_jobs": len(jobs),
            "jobs": jobs
        }
    except Exception as e:
        logger.error(f"获取定时任务报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-queue")
async def get_task_queue_report():
    """
    获取任务队列报表
    """
    try:
        from app.services.task_queue import task_queue
        return await task_queue.get_queue_stats()
    except Exception as e:
        logger.error(f"获取任务队列报表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
