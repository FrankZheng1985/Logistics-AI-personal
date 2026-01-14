"""
视频管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from loguru import logger

from app.models import get_db, Video, VideoStatus

router = APIRouter()


# 请求体模型
class VideoGenerateRequest(BaseModel):
    title: str
    description: str
    video_type: str = "ad"
    keywords: List[str] = []
    voice: str = "zh_female"


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
    request: VideoGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    创建视频生成任务（混合方案）
    
    流程：
    1. 小文撰写脚本
    2. 小视生成AI画面（不含文字）
    3. 后期处理：叠加高清文字 + TTS配音 + 背景音乐
    
    参数：
    - voice: TTS语音类型 (zh_male/zh_female/en_male/en_female)
    """
    from app.agents.copywriter import CopywriterAgent
    from app.agents.video_creator import VideoCreatorAgent
    from app.services.conversation_service import conversation_service
    from loguru import logger
    
    # 从请求体中提取参数
    title = request.title
    description = request.description
    video_type = request.video_type
    keywords = request.keywords
    voice = request.voice
    
    # 创建视频记录
    video = Video(
        title=title,
        description=description,
        video_type=video_type,
        keywords=keywords,
        status=VideoStatus.GENERATING
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    
    try:
        # 第一步：小文生成脚本
        logger.info(f"[小文] 开始为视频 '{title}' 撰写脚本")
        copywriter = CopywriterAgent()
        script_result = await copywriter.process({
            "task_type": "video_script",
            "title": title,
            "description": description,
            "video_type": video_type,
            "keywords": keywords
        })
        
        script = script_result.get("script", description)
        video.script = script
        await conversation_service.record_agent_task("copywriter", True)
        logger.info(f"[小文] 脚本撰写完成")
        
        # 第二步：小视生成视频（混合方案：AI画面 + 文字叠加 + 配音）
        logger.info(f"[小视] 开始生成视频（混合方案）")
        video_creator = VideoCreatorAgent()
        video_result = await video_creator.process({
            "title": title,
            "script": script,
            "keywords": keywords,
            "voice": voice  # 传递TTS语音选项
        })
        await conversation_service.record_agent_task("video_creator", True)
        
        # 更新视频状态
        if video_result.get("status") == "success":
            video.video_url = video_result.get("video_url")
            video.status = VideoStatus.COMPLETED
            message = "视频生成成功！"
        elif video_result.get("status") == "processing":
            # 视频仍在生成中，保存任务ID供后续查询
            video.status = VideoStatus.GENERATING
            message = video_result.get("message", "视频正在生成中，请稍后刷新查看")
        elif video_result.get("status") == "api_not_configured":
            video.status = VideoStatus.DRAFT
            message = "视频脚本已生成，但可灵API未配置，无法生成视频文件"
        else:
            video.status = VideoStatus.FAILED
            message = video_result.get("message", "视频生成失败")
        
        await db.commit()
        logger.info(f"[小视] 视频任务完成: {message}")
        
        return {
            "video_id": str(video.id),
            "status": video.status.value,
            "script": script,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"视频生成失败: {e}")
        video.status = VideoStatus.FAILED
        await db.commit()
        return {
            "video_id": str(video.id),
            "status": "failed",
            "message": f"生成失败: {str(e)}"
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
    
    try:
        # 重新生成视频
        logger.info(f"[小视] 重新生成视频: {video.title}")
        video_creator = VideoCreatorAgent()
        video_result = await video_creator.process({
            "title": video.title,
            "script": video.script or video.description,
            "keywords": video.keywords or []
        })
        
        if video_result.get("status") == "success":
            video.video_url = video_result.get("video_url")
            video.status = VideoStatus.COMPLETED
        elif video_result.get("status") == "processing":
            video.status = VideoStatus.GENERATING
        else:
            video.status = VideoStatus.FAILED
        
        await db.commit()
        
        return {
            "video_id": str(video_id),
            "status": video.status.value,
            "message": "视频重新生成任务已完成"
        }
    except Exception as e:
        logger.error(f"重新生成视频失败: {e}")
        video.status = VideoStatus.FAILED
        await db.commit()
        return {
            "video_id": str(video_id),
            "status": "failed",
            "message": f"重新生成失败: {str(e)}"
        }


@router.delete("/{video_id}")
async def delete_video(
    video_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """删除视频"""
    result = await db.execute(
        select(Video).where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    await db.delete(video)
    await db.commit()
    
    logger.info(f"视频已删除: {video.title}")
    
    return {
        "message": "视频已删除",
        "video_id": str(video_id)
    }
