"""
产品趋势API
提供欧洲跨境电商热门产品趋势的管理接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
from loguru import logger

from app.models.database import get_db


router = APIRouter()


@router.get("")
async def list_product_trends(
    status: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取产品趋势列表
    
    - status: 状态过滤 (new/processed/archived)
    - category: 类别过滤
    - min_score: 最低趋势评分
    - search: 搜索关键词
    """
    try:
        # 构建查询
        query = """
            SELECT id, product_name, category, description, source_url, source_platform,
                   source_region, sales_volume, price_range, growth_rate, trend_score,
                   ai_analysis, ai_opportunity, ai_logistics_tips, keywords,
                   status, is_added_to_knowledge, is_email_sent, 
                   discovered_at, created_at
            FROM product_trends
            WHERE 1=1
        """
        params = {}
        
        if status:
            query += " AND status = :status"
            params["status"] = status
        
        if category:
            query += " AND category = :category"
            params["category"] = category
        
        if min_score:
            query += " AND trend_score >= :min_score"
            params["min_score"] = min_score
        
        if search:
            query += " AND (product_name ILIKE :search OR description ILIKE :search)"
            params["search"] = f"%{search}%"
        
        # 获取总数
        count_query = f"SELECT COUNT(*) FROM ({query}) AS filtered"
        count_result = await db.execute(text(count_query), params)
        total = count_result.scalar() or 0
        
        # 分页
        query += " ORDER BY trend_score DESC, created_at DESC"
        query += " LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        products = []
        for row in rows:
            products.append({
                "id": str(row[0]),
                "product_name": row[1],
                "category": row[2],
                "description": row[3],
                "source_url": row[4],
                "source_platform": row[5],
                "source_region": row[6],
                "sales_volume": row[7],
                "price_range": row[8],
                "growth_rate": row[9],
                "trend_score": row[10],
                "ai_analysis": row[11],
                "ai_opportunity": row[12],
                "ai_logistics_tips": row[13],
                "keywords": row[14] or [],
                "status": row[15],
                "is_added_to_knowledge": row[16],
                "is_email_sent": row[17],
                "discovered_at": row[18].isoformat() if row[18] else None,
                "created_at": row[19].isoformat() if row[19] else None
            })
        
        return {
            "items": products,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error(f"获取产品趋势列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_product_stats(db: AsyncSession = Depends(get_db)):
    """获取产品趋势统计"""
    try:
        from app.agents.lead_hunter import lead_hunter_agent
        stats = await lead_hunter_agent._get_product_stats()
        return stats
    except Exception as e:
        logger.error(f"获取产品统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_product_categories(db: AsyncSession = Depends(get_db)):
    """获取产品类别列表"""
    try:
        result = await db.execute(
            text("""
                SELECT category, COUNT(*) as count
                FROM product_trends
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
            """)
        )
        rows = result.fetchall()
        
        return {
            "categories": [
                {"name": row[0], "count": row[1]}
                for row in rows
            ]
        }
    except Exception as e:
        logger.error(f"获取产品类别失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}")
async def get_product_trend(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个产品趋势详情"""
    try:
        result = await db.execute(
            text("""
                SELECT id, product_name, category, description, source_url, source_platform,
                       source_region, sales_volume, price_range, growth_rate, trend_score,
                       ai_analysis, ai_opportunity, ai_logistics_tips, keywords,
                       status, is_added_to_knowledge, is_email_sent,
                       discovered_at, processed_at, created_at, updated_at
                FROM product_trends
                WHERE id = :id
            """),
            {"id": product_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="产品趋势不存在")
        
        return {
            "id": str(row[0]),
            "product_name": row[1],
            "category": row[2],
            "description": row[3],
            "source_url": row[4],
            "source_platform": row[5],
            "source_region": row[6],
            "sales_volume": row[7],
            "price_range": row[8],
            "growth_rate": row[9],
            "trend_score": row[10],
            "ai_analysis": row[11],
            "ai_opportunity": row[12],
            "ai_logistics_tips": row[13],
            "keywords": row[14] or [],
            "status": row[15],
            "is_added_to_knowledge": row[16],
            "is_email_sent": row[17],
            "discovered_at": row[18].isoformat() if row[18] else None,
            "processed_at": row[19].isoformat() if row[19] else None,
            "created_at": row[20].isoformat() if row[20] else None,
            "updated_at": row[21].isoformat() if row[21] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取产品趋势详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover")
async def discover_product_trends(
    max_keywords: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    触发产品趋势发现任务
    
    - max_keywords: 最大搜索关键词数量
    """
    try:
        from app.agents.lead_hunter import lead_hunter_agent
        
        result = await lead_hunter_agent.process({
            "action": "discover_products",
            "max_keywords": max_keywords
        })
        
        return result
        
    except Exception as e:
        logger.error(f"触发产品趋势发现失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{product_id}")
async def update_product_trend(
    product_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """更新产品趋势状态"""
    try:
        updates = []
        params = {"id": product_id}
        
        if status:
            updates.append("status = :status")
            params["status"] = status
            if status == "processed":
                updates.append("processed_at = NOW()")
        
        if category:
            updates.append("category = :category")
            params["category"] = category
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")
        
        updates.append("updated_at = NOW()")
        
        await db.execute(
            text(f"""
                UPDATE product_trends
                SET {', '.join(updates)}
                WHERE id = :id
            """),
            params
        )
        await db.commit()
        
        return {"success": True, "message": "更新成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新产品趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}")
async def delete_product_trend(
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除产品趋势"""
    try:
        result = await db.execute(
            text("DELETE FROM product_trends WHERE id = :id RETURNING id"),
            {"id": product_id}
        )
        deleted = result.fetchone()
        await db.commit()
        
        if not deleted:
            raise HTTPException(status_code=404, detail="产品趋势不存在")
        
        return {"success": True, "message": "删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除产品趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords/list")
async def list_product_keywords(
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db)
):
    """获取产品趋势搜索关键词列表"""
    try:
        query = """
            SELECT id, keyword, category, platform, priority, is_active, created_at
            FROM product_trend_keywords
            WHERE 1=1
        """
        params = {}
        
        if is_active is not None:
            query += " AND is_active = :is_active"
            params["is_active"] = is_active
        
        if category:
            query += " AND category = :category"
            params["category"] = category
        
        query += " ORDER BY priority DESC, created_at DESC"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        return {
            "keywords": [
                {
                    "id": str(row[0]),
                    "keyword": row[1],
                    "category": row[2],
                    "platform": row[3],
                    "priority": row[4],
                    "is_active": row[5],
                    "created_at": row[6].isoformat() if row[6] else None
                }
                for row in rows
            ]
        }
        
    except Exception as e:
        logger.error(f"获取关键词列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keywords")
async def add_product_keyword(
    keyword: str,
    category: Optional[str] = None,
    platform: Optional[str] = None,
    priority: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """添加产品趋势搜索关键词"""
    try:
        result = await db.execute(
            text("""
                INSERT INTO product_trend_keywords (keyword, category, platform, priority)
                VALUES (:keyword, :category, :platform, :priority)
                RETURNING id
            """),
            {
                "keyword": keyword,
                "category": category,
                "platform": platform,
                "priority": priority
            }
        )
        row = result.fetchone()
        await db.commit()
        
        return {
            "success": True,
            "id": str(row[0]),
            "keyword": keyword
        }
        
    except Exception as e:
        logger.error(f"添加关键词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/keywords/{keyword_id}")
async def delete_product_keyword(
    keyword_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除产品趋势搜索关键词"""
    try:
        result = await db.execute(
            text("DELETE FROM product_trend_keywords WHERE id = :id RETURNING id"),
            {"id": keyword_id}
        )
        deleted = result.fetchone()
        await db.commit()
        
        if not deleted:
            raise HTTPException(status_code=404, detail="关键词不存在")
        
        return {"success": True, "message": "删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除关键词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
