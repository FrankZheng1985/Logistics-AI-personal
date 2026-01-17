"""
内容营销API
管理自动生成的营销内容
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from loguru import logger

from app.models import get_db
from app.services.content_marketing_service import content_marketing_service

router = APIRouter()


# ==================== 请求/响应模型 ====================

class ContentItemUpdate(BaseModel):
    """更新内容条目"""
    title: Optional[str] = None
    content: Optional[str] = None
    hashtags: Optional[List[str]] = None
    call_to_action: Optional[str] = None
    video_script: Optional[str] = None
    status: Optional[str] = None


class GenerateContentRequest(BaseModel):
    """生成内容请求"""
    target_date: Optional[str] = None  # YYYY-MM-DD格式


# ==================== 日历相关API ====================

@router.get("/calendar")
async def get_content_calendar(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取内容日历"""
    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        
        calendar = await content_marketing_service.get_content_calendar(
            start_date=start,
            end_date=end,
            status=status
        )
        
        # 统计
        stats = {
            "total": len(calendar),
            "pending": len([c for c in calendar if c["status"] == "pending"]),
            "generated": len([c for c in calendar if c["status"] == "generated"]),
            "published": len([c for c in calendar if c["status"] == "published"])
        }
        
        return {
            "items": calendar,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取内容日历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/{calendar_id}")
async def get_calendar_detail(
    calendar_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取日历详情（包含所有平台的内容）"""
    try:
        items = await content_marketing_service.get_content_items(calendar_id)
        
        # 获取日历基本信息
        result = await db.execute(
            text("""
                SELECT content_date, content_type, status, topic, data_source
                FROM content_calendar WHERE id = :id
            """),
            {"id": calendar_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="内容日历不存在")
        
        return {
            "id": calendar_id,
            "content_date": str(row[0]),
            "content_type": row[1],
            "status": row[2],
            "topic": row[3],
            "data_source": row[4],
            "items": items
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日历详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 内容生成API ====================

@router.post("/generate")
async def generate_content(
    request: GenerateContentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """生成指定日期的内容"""
    try:
        target = date.fromisoformat(request.target_date) if request.target_date else date.today() + timedelta(days=1)
        
        # 在后台生成内容
        async def generate_task():
            result = await content_marketing_service.generate_daily_content(target)
            logger.info(f"内容生成完成: {result}")
        
        background_tasks.add_task(generate_task)
        
        return {
            "message": "内容生成任务已启动",
            "target_date": str(target),
            "status": "processing"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {e}")
    except Exception as e:
        logger.error(f"启动内容生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/batch")
async def generate_batch_content(
    days: int = Query(7, ge=1, le=30, description="生成未来几天的内容"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """批量生成未来几天的内容"""
    try:
        dates = [date.today() + timedelta(days=i+1) for i in range(days)]
        
        async def batch_generate():
            results = []
            for d in dates:
                result = await content_marketing_service.generate_daily_content(d)
                results.append({"date": str(d), "status": result.get("status")})
            logger.info(f"批量生成完成: {len(results)} 天")
        
        background_tasks.add_task(batch_generate)
        
        return {
            "message": f"已启动未来 {days} 天的内容生成",
            "dates": [str(d) for d in dates],
            "status": "processing"
        }
    except Exception as e:
        logger.error(f"批量生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 内容条目API ====================

@router.get("/items/{item_id}")
async def get_content_item(
    item_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取单个内容条目"""
    try:
        result = await db.execute(
            text("""
                SELECT i.*, c.content_date, c.content_type
                FROM content_items i
                JOIN content_calendar c ON i.calendar_id = c.id
                WHERE i.id = :id
            """),
            {"id": item_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        return {
            "id": str(row[0]),
            "calendar_id": str(row[1]),
            "platform": row[2],
            "title": row[3],
            "content": row[4],
            "hashtags": row[5] or [],
            "cover_prompt": row[6],
            "video_script": row[7],
            "call_to_action": row[8],
            "contact_info": row[9],
            "status": row[10],
            "content_date": str(row[-2]) if row[-2] else None,
            "content_type": row[-1]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取内容条目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/items/{item_id}")
async def update_content_item(
    item_id: str,
    updates: ContentItemUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """更新内容条目"""
    try:
        update_data = updates.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有要更新的内容")
        
        success = await content_marketing_service.update_content_item(item_id, update_data)
        
        if success:
            return {"message": "更新成功"}
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新内容条目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/approve")
async def approve_content_item(
    item_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """审核通过内容"""
    try:
        await db.execute(
            text("UPDATE content_items SET status = 'approved', updated_at = NOW() WHERE id = :id"),
            {"id": item_id}
        )
        await db.commit()
        return {"message": "内容已审核通过"}
    except Exception as e:
        logger.error(f"审核内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/reject")
async def reject_content_item(
    item_id: str,
    reason: str = "",
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """驳回内容"""
    try:
        await db.execute(
            text("UPDATE content_items SET status = 'rejected', updated_at = NOW() WHERE id = :id"),
            {"id": item_id}
        )
        await db.commit()
        return {"message": "内容已驳回"}
    except Exception as e:
        logger.error(f"驳回内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/copy")
async def copy_content(
    item_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """复制内容（用于手动发布）"""
    try:
        result = await db.execute(
            text("SELECT content, title, hashtags, call_to_action FROM content_items WHERE id = :id"),
            {"id": item_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="内容不存在")
        
        # 组合完整文案
        full_content = ""
        if row[1]:  # title
            full_content += f"{row[1]}\n\n"
        full_content += row[0]  # content
        if row[3]:  # call_to_action
            full_content += f"\n\n{row[3]}"
        if row[2]:  # hashtags
            full_content += f"\n\n{' '.join(['#' + tag for tag in row[2]])}"
        
        return {
            "content": full_content,
            "message": "内容已复制"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"复制内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计API ====================

@router.get("/stats")
async def get_content_stats(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取内容统计"""
    try:
        start_date = date.today() - timedelta(days=days)
        
        # 内容生成统计
        result = await db.execute(
            text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'generated' THEN 1 END) as generated,
                    COUNT(CASE WHEN status = 'published' THEN 1 END) as published
                FROM content_calendar
                WHERE content_date >= :start
            """),
            {"start": start_date}
        )
        calendar_stats = result.fetchone()
        
        # 按平台统计
        result = await db.execute(
            text("""
                SELECT 
                    platform,
                    COUNT(*) as count,
                    SUM(COALESCE(views, 0)) as total_views,
                    SUM(COALESCE(leads_generated, 0)) as total_leads
                FROM content_items i
                JOIN content_calendar c ON i.calendar_id = c.id
                WHERE c.content_date >= :start
                GROUP BY platform
            """),
            {"start": start_date}
        )
        platform_stats = {
            row[0]: {
                "count": row[1],
                "views": row[2] or 0,
                "leads": row[3] or 0
            }
            for row in result.fetchall()
        }
        
        # 按内容类型统计
        result = await db.execute(
            text("""
                SELECT content_type, COUNT(*) as count
                FROM content_calendar
                WHERE content_date >= :start
                GROUP BY content_type
            """),
            {"start": start_date}
        )
        type_stats = {row[0]: row[1] for row in result.fetchall()}
        
        return {
            "period_days": days,
            "calendar": {
                "total": calendar_stats[0] or 0,
                "generated": calendar_stats[1] or 0,
                "published": calendar_stats[2] or 0
            },
            "by_platform": platform_stats,
            "by_type": type_stats
        }
    except Exception as e:
        logger.error(f"获取内容统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 模板API ====================

@router.get("/templates")
async def get_content_templates(
    content_type: Optional[str] = None,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """获取内容模板"""
    try:
        query = """
            SELECT id, name, content_type, platform, title_template, 
                   content_template, hashtags_template, cta_template,
                   is_active, use_count, created_at
            FROM content_templates
            WHERE 1=1
        """
        params = {}
        
        if content_type:
            query += " AND content_type = :type"
            params["type"] = content_type
        if platform:
            query += " AND platform = :platform"
            params["platform"] = platform
        
        query += " ORDER BY use_count DESC, created_at DESC"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        return {
            "items": [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "content_type": row[2],
                    "platform": row[3],
                    "title_template": row[4],
                    "content_template": row[5],
                    "hashtags_template": row[6] or [],
                    "cta_template": row[7],
                    "is_active": row[8],
                    "use_count": row[9],
                    "created_at": row[10].isoformat() if row[10] else None
                }
                for row in rows
            ],
            "total": len(rows)
        }
    except Exception as e:
        logger.error(f"获取内容模板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
