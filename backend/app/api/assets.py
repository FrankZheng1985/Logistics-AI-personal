"""
素材库管理API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
import os
import aiofiles
from loguru import logger

from app.models.database import AsyncSessionLocal

router = APIRouter(prefix="/assets", tags=["素材库"])

# 配置
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/uploads/assets")
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/x-msvideo"]
ALLOWED_AUDIO_TYPES = ["audio/mpeg", "audio/wav", "audio/ogg"]
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]


class AssetCreate(BaseModel):
    name: str
    type: str  # video, audio, image
    category: str
    duration: Optional[int] = None


class AssetResponse(BaseModel):
    id: str
    name: str
    type: str
    category: str
    duration: Optional[int]
    file_size: int
    file_url: Optional[str]
    thumbnail_url: Optional[str]
    usage_count: int
    created_at: str


@router.get("")
async def list_assets(
    type: Optional[str] = Query(None, description="素材类型: video, audio, image"),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取素材列表"""
    try:
        async with AsyncSessionLocal() as db:
            # 构建查询
            sql = """
                SELECT id, name, type, category, duration, file_size, 
                       file_url, thumbnail_url, usage_count, created_at
                FROM assets
                WHERE 1=1
            """
            params = {"limit": page_size, "offset": (page - 1) * page_size}
            
            if type:
                sql += " AND type = :type"
                params["type"] = type
            
            if category:
                sql += " AND category = :category"
                params["category"] = category
            
            # 统计总数
            count_sql = f"SELECT COUNT(*) FROM ({sql}) AS sub"
            count_result = await db.execute(text(count_sql.replace("SELECT id, name, type, category, duration, file_size, file_url, thumbnail_url, usage_count, created_at", "SELECT id")), params)
            total = count_result.scalar() or 0
            
            # 分页查询
            sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            items = [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "type": row[2],
                    "category": row[3],
                    "duration": row[4],
                    "file_size": row[5] or 0,
                    "file_url": row[6],
                    "thumbnail_url": row[7],
                    "usage_count": row[8] or 0,
                    "created_at": row[9].isoformat() if row[9] else None
                }
                for row in rows
            ]
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size
            }
    except Exception as e:
        logger.error(f"获取素材列表失败: {e}")
        # 返回空列表而不是报错
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }


@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    category: str = "general"
):
    """上传素材"""
    try:
        # 确定素材类型
        content_type = file.content_type or ""
        if content_type in ALLOWED_VIDEO_TYPES:
            asset_type = "video"
        elif content_type in ALLOWED_AUDIO_TYPES:
            asset_type = "audio"
        elif content_type in ALLOWED_IMAGE_TYPES:
            asset_type = "image"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {content_type}")
        
        # 创建上传目录
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(file.filename)[1] if file.filename else ""
        filename = f"{asset_type}_{timestamp}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # 保存文件
        file_size = 0
        async with aiofiles.open(filepath, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await f.write(chunk)
                file_size += len(chunk)
        
        # 保存到数据库
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO assets (name, type, category, file_size, file_url, created_at)
                    VALUES (:name, :type, :category, :file_size, :file_url, NOW())
                    RETURNING id
                """),
                {
                    "name": name or file.filename or filename,
                    "type": asset_type,
                    "category": category,
                    "file_size": file_size,
                    "file_url": f"/uploads/assets/{filename}"
                }
            )
            asset_id = result.scalar()
            await db.commit()
        
        logger.info(f"素材上传成功: {filename}, 大小: {file_size}")
        
        return {
            "id": str(asset_id),
            "name": name or file.filename,
            "type": asset_type,
            "file_url": f"/uploads/assets/{filename}",
            "file_size": file_size,
            "message": "上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"素材上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{asset_id}")
async def get_asset(asset_id: str):
    """获取素材详情"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, name, type, category, duration, file_size, 
                           file_url, thumbnail_url, usage_count, created_at
                    FROM assets WHERE id = :id
                """),
                {"id": asset_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="素材不存在")
            
            return {
                "id": str(row[0]),
                "name": row[1],
                "type": row[2],
                "category": row[3],
                "duration": row[4],
                "file_size": row[5] or 0,
                "file_url": row[6],
                "thumbnail_url": row[7],
                "usage_count": row[8] or 0,
                "created_at": row[9].isoformat() if row[9] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取素材详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str):
    """删除素材"""
    try:
        async with AsyncSessionLocal() as db:
            # 获取文件路径
            result = await db.execute(
                text("SELECT file_url FROM assets WHERE id = :id"),
                {"id": asset_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="素材不存在")
            
            # 删除数据库记录
            await db.execute(
                text("DELETE FROM assets WHERE id = :id"),
                {"id": asset_id}
            )
            await db.commit()
            
            # 尝试删除文件
            if row[0]:
                filepath = os.path.join("/app", row[0].lstrip("/"))
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            return {"message": "素材已删除"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除素材失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{asset_id}/use")
async def record_asset_usage(asset_id: str):
    """记录素材使用次数"""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("UPDATE assets SET usage_count = usage_count + 1 WHERE id = :id"),
                {"id": asset_id}
            )
            await db.commit()
            
            return {"message": "使用次数已更新"}
    except Exception as e:
        logger.error(f"更新使用次数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
