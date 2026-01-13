"""
视频管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.models import get_db, Video, VideoStatus, AITask

router = APIRouter()


@router.get("")
async def list_videos(
    status: Optional[VideoStatus] = None,
    video_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取视频列表"""
    query = select(Video)
    
    if status:
        query = query.where(Video.status == status)
    
    if video_type:
        query = query.where(Video.video_type == video_type)
    
    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页
    query = query.order_by(Video.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    videos = result.scalars().all()
    
    return {
        "items": [
            {
                "id": str(v.id),
                "title": v.title,
                "description": v.description,
                "video_type": v.video_type,
                "status": v.status.value,
                "video_url": v.video_url,
                "thumbnail_url": v.thumbnail_url,
                "duration": v.duration,
                "created_at": v.created_at.isoformat()
            }
            for v in videos
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{video_id}")
async def get_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取视频详情"""
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return {
        "id": str(video.id),
        "title": video.title,
        "description": video.description,
        "video_type": video.video_type,
        "script": video.script,
        "keywords": video.keywords,
        "status": video.status.value,
        "video_url": video.video_url,
        "thumbnail_url": video.thumbnail_url,
        "duration": video.duration,
        "file_size": video.file_size,
        "created_at": video.created_at.isoformat(),
        "updated_at": video.updated_at.isoformat()
    }


@router.post("/generate")
async def generate_video(
    title: str,
    description: str,
    video_type: str = "ad",
    keywords: list[str] = [],
    db: AsyncSession = Depends(get_db)
):
    """
    创建视频生成任务
    这个接口会触发小文生成脚本，然后小视生成视频
    """
    # 创建视频记录
    video = Video(
        title=title,
        description=description,
        video_type=video_type,
        keywords=keywords,
        status=VideoStatus.DRAFT
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    
    # TODO: 创建AI任务，由小调分配给小文和小视
    
    return {
        "video_id": str(video.id),
        "status": "task_created",
        "message": "视频生成任务已创建，小文正在撰写脚本..."
    }


@router.post("/{video_id}/regenerate")
async def regenerate_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """重新生成视频"""
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    video.status = VideoStatus.GENERATING
    await db.commit()
    
    # TODO: 重新触发视频生成任务
    
    return {
        "video_id": str(video_id),
        "status": "regenerating",
        "message": "正在重新生成视频..."
    }
