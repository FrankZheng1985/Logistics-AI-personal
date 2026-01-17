"""
内容管理API
包括：文案列表、发布、审核等
支持：企业微信、小红书等渠道
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services.content_publisher import content_publisher
from app.services.xiaohongshu_publisher import xiaohongshu_publisher
from app.services.multi_platform_publisher import multi_platform_publisher

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


# ==================== 小红书发布 ====================

class XhsPublishRequest(BaseModel):
    """小红书发布请求"""
    content_id: str
    image_urls: Optional[List[str]] = None


@router.post("/posts/{content_id}/publish-to-xhs")
async def publish_to_xiaohongshu(content_id: str, image_urls: Optional[List[str]] = None):
    """
    发布文案到小红书
    
    如果已配置小红书API，会直接发布；
    否则会发送格式化文案到企业微信，用户手动复制发布。
    
    Args:
        content_id: 文案ID
        image_urls: 配图URL列表（可选）
    """
    result = await xiaohongshu_publisher.publish(
        content_id=content_id,
        image_urls=image_urls
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "发布失败")
        )
    
    return result


@router.post("/posts/{content_id}/format-for-xhs")
async def format_for_xiaohongshu(content_id: str):
    """
    将文案格式化为小红书风格（预览）
    
    返回格式化后的标题、正文和话题标签
    """
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    async with async_session_maker() as db:
        result = await db.execute(
            text("""
                SELECT content, topic
                FROM content_posts
                WHERE id = :id
            """),
            {"id": content_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="文案不存在")
        
        content = row[0]
        topic = row[1]
    
    # 格式化
    formatted = xiaohongshu_publisher.format_for_xiaohongshu(content, topic)
    
    return {
        "original_content": content,
        "formatted": formatted,
        "tips": [
            "标题最多20字，正文最多1000字",
            "建议配3-9张高质量图片",
            "最佳发布时间：12:00-14:00 或 20:00-22:00",
            "话题标签已自动添加在正文末尾"
        ]
    }


@router.post("/quick-publish-xhs")
async def quick_publish_to_xiaohongshu(
    topic: str,
    image_urls: Optional[List[str]] = None
):
    """
    快速生成小红书文案并发布
    
    Args:
        topic: 文案主题（如：欧洲物流干货）
        image_urls: 配图URL列表
    """
    from app.agents.copywriter import copywriter_agent
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    # 生成小红书风格文案
    result = await copywriter_agent.process({
        "task_type": "xiaohongshu",  # 使用小红书专用模板
        "topic": topic,
        "purpose": "种草分享",
        "target_audience": "外贸人、跨境电商卖家"
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
                VALUES (:content, :topic, 'xiaohongshu', 'approved', NOW())
                RETURNING id
            """),
            {
                "content": copy,
                "topic": topic
            }
        )
        row = insert_result.fetchone()
        content_id = str(row[0])
        await db.commit()
    
    # 发布到小红书
    publish_result = await xiaohongshu_publisher.publish(
        content_id=content_id,
        image_urls=image_urls
    )
    
    return {
        "success": True,
        "content_id": content_id,
        "topic": topic,
        "publish_result": publish_result
    }


# ==================== 多平台发布 ====================

@router.get("/platforms")
async def get_available_platforms():
    """
    获取所有支持的发布平台
    
    返回各平台的配置状态和限制要求
    """
    platforms = multi_platform_publisher.get_available_platforms()
    return {
        "platforms": platforms,
        "total": len(platforms)
    }


class MultiPublishRequest(BaseModel):
    """多平台发布请求"""
    platforms: List[str]


@router.post("/posts/{content_id}/publish-multi")
async def publish_to_multi_platforms(
    content_id: str,
    request: MultiPublishRequest
):
    """
    发布文案到多个平台
    
    Args:
        content_id: 文案ID
        platforms: 平台列表，如 ["zhihu", "csdn", "toutiao"]
    
    支持的平台:
        - zhihu: 知乎
        - csdn: CSDN博客
        - jianshu: 简书
        - toutiao: 今日头条
        - weibo: 微博
        - baijiahao: 百家号
        - wordpress: WordPress网站
        - wechat_article: 微信公众号
    """
    result = await multi_platform_publisher.publish(
        content_id=content_id,
        platforms=request.platforms
    )
    
    return result


@router.post("/posts/{content_id}/publish-all")
async def publish_to_all_platforms(content_id: str):
    """
    一键发布到所有推荐平台
    
    会发送格式化好的文案到企业微信，方便手动复制到各平台
    """
    result = await multi_platform_publisher.batch_publish(
        content_id=content_id,
        all_platforms=True
    )
    
    return result


@router.post("/posts/{content_id}/format-for-platform")
async def format_for_platform(content_id: str, platform: str):
    """
    为指定平台格式化文案（预览）
    
    Args:
        content_id: 文案ID
        platform: 目标平台
    """
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    async with async_session_maker() as db:
        result = await db.execute(
            text("""
                SELECT content, topic
                FROM content_posts
                WHERE id = :id
            """),
            {"id": content_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="文案不存在")
        
        content = row[0]
        topic = row[1]
    
    # 格式化
    formatted = multi_platform_publisher.format_for_platform(content, topic, platform)
    platform_info = multi_platform_publisher.PLATFORMS.get(platform, {})
    
    return {
        "original_content": content,
        "formatted": formatted,
        "platform_info": {
            "name": platform_info.get("name"),
            "icon": platform_info.get("icon"),
            "max_title": platform_info.get("max_title"),
            "max_content": platform_info.get("max_content")
        }
    }


@router.post("/quick-publish-multi")
async def quick_publish_to_multi_platforms(
    topic: str,
    platforms: List[str],
    article_type: str = "professional"
):
    """
    快速生成并发布到多个平台
    
    Args:
        topic: 文案主题
        platforms: 目标平台列表
        article_type: 文章类型 (professional/casual/story)
    """
    from app.agents.copywriter import copywriter_agent
    from sqlalchemy import text
    from app.models.database import async_session_maker
    
    # 根据平台类型选择文案风格
    task_type = "article" if article_type == "professional" else "moments"
    
    # 生成文案
    result = await copywriter_agent.process({
        "task_type": task_type,
        "topic": topic,
        "purpose": "行业知识分享",
        "target_audience": "外贸人、跨境电商卖家、物流从业者"
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
                VALUES (:content, :topic, 'multi', 'approved', NOW())
                RETURNING id
            """),
            {
                "content": copy,
                "topic": topic
            }
        )
        row = insert_result.fetchone()
        content_id = str(row[0])
        await db.commit()
    
    # 发布到多个平台
    publish_result = await multi_platform_publisher.publish(
        content_id=content_id,
        platforms=platforms
    )
    
    return {
        "success": True,
        "content_id": content_id,
        "topic": topic,
        "platforms": platforms,
        "publish_result": publish_result
    }
