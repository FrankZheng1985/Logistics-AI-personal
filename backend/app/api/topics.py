"""
热门话题API - 小猎话题发现模式
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from app.models import get_db

router = APIRouter()


class TopicUpdate(BaseModel):
    status: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None


@router.get("")
async def list_topics(
    status: Optional[str] = Query(None, description="筛选状态: new, answered, skipped"),
    platform: Optional[str] = Query(None, description="筛选平台: zhihu, xiaohongshu"),
    priority: Optional[str] = Query(None, description="筛选优先级: high, medium, low"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取热门话题列表"""
    
    # 构建查询条件
    conditions = []
    params = {"offset": (page - 1) * page_size, "limit": page_size}
    
    if status:
        conditions.append("status = :status")
        params["status"] = status
    
    if platform:
        conditions.append("platform = :platform")
        params["platform"] = platform
    
    if priority:
        conditions.append("priority = :priority")
        params["priority"] = priority
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    # 查询总数
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM hot_topics WHERE {where_clause}"),
        params
    )
    total = count_result.scalar() or 0
    
    # 查询数据
    result = await db.execute(
        text(f"""
            SELECT id, title, url, platform, category, keywords,
                   value_score, ai_summary, ai_answer_strategy, ai_recommended_points,
                   status, priority, generated_content, generated_at,
                   published_at, discovered_at
            FROM hot_topics 
            WHERE {where_clause}
            ORDER BY 
                CASE WHEN status = 'new' THEN 0 ELSE 1 END,
                value_score DESC,
                discovered_at DESC
            OFFSET :offset LIMIT :limit
        """),
        params
    )
    topics = result.fetchall()
    
    return {
        "items": [
            {
                "id": str(row[0]),
                "title": row[1],
                "url": row[2],
                "platform": row[3],
                "category": row[4],
                "keywords": row[5] or [],
                "value_score": row[6],
                "ai_summary": row[7],
                "ai_answer_strategy": row[8],
                "ai_recommended_points": row[9] or [],
                "status": row[10],
                "priority": row[11],
                "generated_content": row[12],
                "generated_at": row[13].isoformat() if row[13] else None,
                "published_at": row[14].isoformat() if row[14] else None,
                "discovered_at": row[15].isoformat() if row[15] else None
            }
            for row in topics
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/stats")
async def get_topic_stats(db: AsyncSession = Depends(get_db)):
    """获取话题统计"""
    
    # 总话题数
    total_result = await db.execute(text("SELECT COUNT(*) FROM hot_topics"))
    total = total_result.scalar() or 0
    
    # 待回答
    new_result = await db.execute(
        text("SELECT COUNT(*) FROM hot_topics WHERE status = 'new'")
    )
    new_count = new_result.scalar() or 0
    
    # 已回答
    answered_result = await db.execute(
        text("SELECT COUNT(*) FROM hot_topics WHERE status = 'answered'")
    )
    answered_count = answered_result.scalar() or 0
    
    # 高价值
    high_value_result = await db.execute(
        text("SELECT COUNT(*) FROM hot_topics WHERE value_score >= 70 AND status = 'new'")
    )
    high_value_count = high_value_result.scalar() or 0
    
    # 今日发现
    today_result = await db.execute(
        text("SELECT COUNT(*) FROM hot_topics WHERE DATE(discovered_at) = CURRENT_DATE")
    )
    today_count = today_result.scalar() or 0
    
    # 按平台统计
    platform_result = await db.execute(
        text("""
            SELECT platform, COUNT(*) 
            FROM hot_topics 
            GROUP BY platform
        """)
    )
    by_platform = {row[0]: row[1] for row in platform_result.fetchall()}
    
    # 按状态统计
    status_result = await db.execute(
        text("""
            SELECT status, COUNT(*) 
            FROM hot_topics 
            GROUP BY status
        """)
    )
    by_status = {row[0]: row[1] for row in status_result.fetchall()}
    
    return {
        "total": total,
        "new": new_count,
        "answered": answered_count,
        "high_value": high_value_count,
        "today": today_count,
        "by_platform": by_platform,
        "by_status": by_status
    }


@router.get("/{topic_id}")
async def get_topic(topic_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取话题详情"""
    
    result = await db.execute(
        text("""
            SELECT id, title, url, platform, category, keywords,
                   value_score, ai_summary, ai_answer_strategy, ai_recommended_points,
                   status, priority, generated_content, generated_at,
                   published_at, published_by, discovered_at
            FROM hot_topics WHERE id = :id
        """),
        {"id": topic_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="话题不存在")
    
    return {
        "id": str(row[0]),
        "title": row[1],
        "url": row[2],
        "platform": row[3],
        "category": row[4],
        "keywords": row[5] or [],
        "value_score": row[6],
        "ai_summary": row[7],
        "ai_answer_strategy": row[8],
        "ai_recommended_points": row[9] or [],
        "status": row[10],
        "priority": row[11],
        "generated_content": row[12],
        "generated_at": row[13].isoformat() if row[13] else None,
        "published_at": row[14].isoformat() if row[14] else None,
        "published_by": row[15],
        "discovered_at": row[16].isoformat() if row[16] else None
    }


@router.post("/discover")
async def discover_topics(
    background_tasks: BackgroundTasks,
    max_keywords: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """启动话题发现任务"""
    from app.agents.lead_hunter import lead_hunter_agent
    from app.core.config import settings
    
    # 检查API配置
    if not getattr(settings, 'SERPER_API_KEY', None):
        raise HTTPException(
            status_code=400,
            detail="搜索API未配置。请在系统设置中配置 SERPER_API_KEY。"
        )
    
    async def run_discovery():
        try:
            results = await lead_hunter_agent.process({
                "action": "discover_topics",
                "max_keywords": max_keywords
            })
            logger.info(f"话题发现完成: 发现 {results.get('total_topics', 0)} 个话题")
        except Exception as e:
            logger.error(f"话题发现失败: {e}")
    
    background_tasks.add_task(run_discovery)
    
    return {
        "message": "话题发现任务已启动",
        "status": "running"
    }


@router.post("/{topic_id}/generate")
async def generate_answer(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """为话题生成回答内容"""
    from app.agents.lead_hunter import lead_hunter_agent
    
    result = await lead_hunter_agent.process({
        "action": "generate_answer",
        "topic_id": str(topic_id)
    })
    
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.patch("/{topic_id}")
async def update_topic(
    topic_id: UUID,
    update_data: TopicUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新话题状态"""
    
    # 检查话题是否存在
    check_result = await db.execute(
        text("SELECT id FROM hot_topics WHERE id = :id"),
        {"id": topic_id}
    )
    if not check_result.fetchone():
        raise HTTPException(status_code=404, detail="话题不存在")
    
    # 构建更新语句
    updates = []
    params = {"id": topic_id}
    
    if update_data.status:
        updates.append("status = :status")
        params["status"] = update_data.status
    
    if update_data.published_at:
        updates.append("published_at = :published_at")
        params["published_at"] = update_data.published_at
    
    if update_data.published_by:
        updates.append("published_by = :published_by")
        params["published_by"] = update_data.published_by
    
    if updates:
        updates.append("updated_at = NOW()")
        await db.execute(
            text(f"UPDATE hot_topics SET {', '.join(updates)} WHERE id = :id"),
            params
        )
        await db.commit()
    
    return {"message": "更新成功"}


@router.post("/{topic_id}/mark-answered")
async def mark_topic_answered(
    topic_id: UUID,
    published_by: str = Query("", description="发布人"),
    db: AsyncSession = Depends(get_db)
):
    """标记话题为已回答"""
    
    await db.execute(
        text("""
            UPDATE hot_topics 
            SET status = 'answered',
                published_at = NOW(),
                published_by = :published_by,
                updated_at = NOW()
            WHERE id = :id
        """),
        {"id": topic_id, "published_by": published_by}
    )
    await db.commit()
    
    return {"message": "已标记为已回答"}


@router.post("/{topic_id}/skip")
async def skip_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """跳过话题（不回答）"""
    
    await db.execute(
        text("""
            UPDATE hot_topics 
            SET status = 'skipped',
                updated_at = NOW()
            WHERE id = :id
        """),
        {"id": topic_id}
    )
    await db.commit()
    
    return {"message": "已跳过"}


@router.delete("/{topic_id}")
async def delete_topic(
    topic_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """删除话题"""
    
    await db.execute(
        text("DELETE FROM hot_topics WHERE id = :id"),
        {"id": topic_id}
    )
    await db.commit()
    
    return {"message": "已删除"}
