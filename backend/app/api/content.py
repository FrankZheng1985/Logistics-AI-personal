"""
内容管理API
包括：文案列表、发布、审核等
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services.content_publisher import content_publisher

router = APIRouter(prefix="/content", tags=["内容管理"])


class PublishRequest(BaseModel):
    """发布请求"""
    content_id: str
    channels: List[str] = ["wechat_app"]  # 默认发送到企业微信应用


class ApproveRequest(BaseModel):
    """审核请求"""
    content_id: str
    approved: bool = True


@router.get("/posts")
async def get_content_posts(
    status: Optional[str] = None,
    limit: int = 20
):
    """
    获取文案列表
    
    Args:
        status: 状态筛选 (draft/approved/published)
        limit: 返回数量
    """
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    async with async_session_maker() as db:
        query = """
            SELECT id, content, topic, platform, status, created_at, published_at
            FROM content_posts
        """
        params = {"limit": limit}
        
        if status:
            query += " WHERE status = :status"
            params["status"] = status
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        
        result = await db.execute(text(query), params)
        rows = result.fetchall()
        
        return {
            "posts": [
                {
                    "id": str(row[0]),
                    "content": row[1],
                    "topic": row[2],
                    "platform": row[3],
                    "status": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "published_at": row[6].isoformat() if row[6] else None
                }
                for row in rows
            ],
            "total": len(rows)
        }


@router.get("/posts/{content_id}")
async def get_content_post(content_id: str):
    """获取单个文案详情"""
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    async with async_session_maker() as db:
        result = await db.execute(
            text("""
                SELECT id, content, topic, platform, status, 
                       created_at, published_at, published_channels
                FROM content_posts
                WHERE id = :id
            """),
            {"id": content_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="文案不存在")
        
        return {
            "id": str(row[0]),
            "content": row[1],
            "topic": row[2],
            "platform": row[3],
            "status": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "published_at": row[6].isoformat() if row[6] else None,
            "published_channels": row[7]
        }


@router.post("/posts/{content_id}/approve")
async def approve_content(content_id: str, request: ApproveRequest):
    """
    审核文案
    
    Args:
        content_id: 文案ID
        request: 审核请求（approved=True 通过，False 拒绝）
    """
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    new_status = "approved" if request.approved else "rejected"
    
    async with async_session_maker() as db:
        result = await db.execute(
            text("""
                UPDATE content_posts
                SET status = :status,
                    updated_at = NOW()
                WHERE id = :id AND status = 'draft'
                RETURNING id
            """),
            {"id": content_id, "status": new_status}
        )
        row = result.fetchone()
        await db.commit()
        
        if not row:
            raise HTTPException(status_code=400, detail="文案不存在或状态不是草稿")
        
        return {
            "success": True,
            "content_id": content_id,
            "new_status": new_status,
            "message": f"文案已{'通过审核' if request.approved else '被拒绝'}"
        }


@router.post("/posts/{content_id}/publish")
async def publish_content(content_id: str, request: PublishRequest):
    """
    发布文案到指定渠道
    
    Args:
        content_id: 文案ID
        request: 发布请求
    
    支持的渠道:
        - wechat_app: 企业微信应用消息
        - wechat_moments: 企业微信客户朋友圈
    """
    result = await content_publisher.publish_content(
        content_id=content_id,
        channels=request.channels
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400, 
            detail=result.get("error", "发布失败")
        )
    
    return result


@router.post("/publish-all-approved")
async def publish_all_approved():
    """
    发布所有已审核的文案
    """
    result = await content_publisher.auto_publish_approved()
    return result


@router.get("/pending")
async def get_pending_contents(limit: int = 10):
    """获取待发布（草稿）的文案列表"""
    contents = await content_publisher.get_pending_contents(limit=limit)
    return {
        "contents": contents,
        "total": len(contents)
    }


@router.post("/quick-publish")
async def quick_publish(
    topic: str,
    auto_publish: bool = False
):
    """
    快速生成并发布文案
    
    Args:
        topic: 文案主题
        auto_publish: 是否自动发布（默认只生成草稿）
    """
    from app.agents.copywriter import copywriter_agent
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    # 生成文案
    result = await copywriter_agent.process({
        "task_type": "moments",
        "topic": topic,
        "purpose": "营销推广",
        "target_audience": "有物流需求的客户"
    })
    
    copy = result.get("copy", "")
    if not copy:
        raise HTTPException(status_code=500, detail="文案生成失败")
    
    # 保存文案
    async with async_session_maker() as db:
        insert_result = await db.execute(
            text("""
                INSERT INTO content_posts 
                (content, topic, platform, status, created_at)
                VALUES (:content, :topic, 'wechat_moments', :status, NOW())
                RETURNING id
            """),
            {
                "content": copy,
                "topic": topic,
                "status": "approved" if auto_publish else "draft"
            }
        )
        row = insert_result.fetchone()
        content_id = str(row[0])
        await db.commit()
    
    response = {
        "success": True,
        "content_id": content_id,
        "content": copy,
        "topic": topic,
        "status": "approved" if auto_publish else "draft"
    }
    
    # 如果需要自动发布
    if auto_publish:
        publish_result = await content_publisher.publish_content(
            content_id=content_id,
            channels=["wechat_app"]
        )
        response["publish_result"] = publish_result
    
    return response
