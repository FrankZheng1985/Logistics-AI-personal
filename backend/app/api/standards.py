"""
工作标准管理API
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.models.database import AsyncSessionLocal

router = APIRouter(prefix="/standards", tags=["standards"])


class StandardResponse(BaseModel):
    id: str
    agent_type: str
    standard_category: str
    standard_name: str
    standard_content: dict
    quality_metrics: dict
    version: int
    is_active: bool


class StandardUpdate(BaseModel):
    standard_content: Optional[dict] = None
    quality_metrics: Optional[dict] = None


@router.get("", response_model=List[StandardResponse])
async def get_all_standards(agent_type: Optional[str] = None):
    """获取所有工作标准"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            sql = """
                SELECT id, agent_type, standard_category, standard_name, 
                       standard_content, quality_metrics, version, is_active
                FROM agent_standards
                WHERE is_active = TRUE
            """
            params = {}
            
            if agent_type:
                sql += " AND agent_type = :agent_type"
                params["agent_type"] = agent_type
            
            sql += " ORDER BY agent_type, standard_category"
            
            result = await db.execute(text(sql), params)
            rows = result.fetchall()
            
            return [
                StandardResponse(
                    id=str(row[0]),
                    agent_type=row[1],
                    standard_category=row[2],
                    standard_name=row[3],
                    standard_content=row[4],
                    quality_metrics=row[5],
                    version=row[6],
                    is_active=row[7]
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{standard_id}", response_model=StandardResponse)
async def get_standard(standard_id: str):
    """获取单个工作标准"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            
            result = await db.execute(
                text("""
                    SELECT id, agent_type, standard_category, standard_name, 
                           standard_content, quality_metrics, version, is_active
                    FROM agent_standards
                    WHERE id = :id
                """),
                {"id": standard_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="标准不存在")
            
            return StandardResponse(
                id=str(row[0]),
                agent_type=row[1],
                standard_category=row[2],
                standard_name=row[3],
                standard_content=row[4],
                quality_metrics=row[5],
                version=row[6],
                is_active=row[7]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{standard_id}")
async def update_standard(standard_id: str, update: StandardUpdate):
    """更新工作标准"""
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            import json
            
            # 获取当前版本
            result = await db.execute(
                text("SELECT version, standard_content, quality_metrics FROM agent_standards WHERE id = :id"),
                {"id": standard_id}
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="标准不存在")
            
            current_version = row[0]
            
            # 保存历史版本
            await db.execute(
                text("""
                    INSERT INTO agent_standards_history 
                    (standard_id, version, standard_content, quality_metrics, created_at)
                    VALUES (:id, :version, :content, :metrics, NOW())
                """),
                {
                    "id": standard_id,
                    "version": current_version,
                    "content": json.dumps(row[1]),
                    "metrics": json.dumps(row[2])
                }
            )
            
            # 更新标准
            updates = []
            params = {"id": standard_id}
            
            if update.standard_content:
                updates.append("standard_content = :content")
                params["content"] = json.dumps(update.standard_content)
            
            if update.quality_metrics:
                updates.append("quality_metrics = :metrics")
                params["metrics"] = json.dumps(update.quality_metrics)
            
            if updates:
                updates.append("version = version + 1")
                updates.append("updated_at = NOW()")
                
                await db.execute(
                    text(f"UPDATE agent_standards SET {', '.join(updates)} WHERE id = :id"),
                    params
                )
            
            await db.commit()
            
            return {"message": "标准更新成功", "new_version": current_version + 1}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
