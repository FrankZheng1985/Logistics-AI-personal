"""
知识库API
提供知识的增删改查接口
"""
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Body
from pydantic import BaseModel
from loguru import logger

from app.services.knowledge_base import knowledge_base, KNOWLEDGE_TYPES

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class KnowledgeCreate(BaseModel):
    """创建知识请求"""
    content: str
    knowledge_type: str
    tags: List[str] = []
    is_verified: bool = False


class KnowledgeUpdate(BaseModel):
    """更新知识请求"""
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    is_verified: Optional[bool] = None


@router.get("/types")
async def get_knowledge_types():
    """获取知识类型列表"""
    return {
        "types": [
            {"type": k, **v}
            for k, v in KNOWLEDGE_TYPES.items()
        ]
    }


@router.get("/")
async def list_knowledge(
    knowledge_type: Optional[str] = Query(None, description="知识类型"),
    query: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """获取知识列表"""
    try:
        if query:
            results = await knowledge_base.search_knowledge(
                query=query,
                knowledge_type=knowledge_type,
                limit=limit
            )
        else:
            from app.models.database import async_session_maker
            from sqlalchemy import text
            
            async with async_session_maker() as db:
                sql = """
                    SELECT id, content, knowledge_type, source, tags, 
                           is_verified, usage_count, created_at
                    FROM knowledge_base
                """
                params = {"limit": limit, "offset": offset}
                
                if knowledge_type:
                    sql += " WHERE knowledge_type = :type"
                    params["type"] = knowledge_type
                
                sql += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                
                result = await db.execute(text(sql), params)
                rows = result.fetchall()
                
                results = [
                    {
                        "id": str(row[0]),
                        "content": row[1],
                        "knowledge_type": row[2],
                        "type_name": KNOWLEDGE_TYPES.get(row[2], {}).get("name", row[2]),
                        "source": row[3],
                        "tags": row[4],
                        "is_verified": row[5],
                        "usage_count": row[6],
                        "created_at": row[7].isoformat() if row[7] else None
                    }
                    for row in rows
                ]
        
        return {"items": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"获取知识列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_knowledge(data: KnowledgeCreate):
    """创建知识"""
    try:
        knowledge_id = await knowledge_base.add_knowledge(
            content=data.content,
            knowledge_type=data.knowledge_type,
            source="manual",
            tags=data.tags,
            is_verified=data.is_verified
        )
        
        if knowledge_id:
            return {"id": knowledge_id, "message": "创建成功"}
        else:
            raise HTTPException(status_code=500, detail="创建失败")
            
    except Exception as e:
        logger.error(f"创建知识失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{knowledge_id}")
async def update_knowledge(knowledge_id: str, data: KnowledgeUpdate):
    """更新知识"""
    try:
        success = await knowledge_base.update_knowledge(
            knowledge_id=knowledge_id,
            content=data.content,
            tags=data.tags,
            is_verified=data.is_verified
        )
        
        if success:
            return {"message": "更新成功"}
        else:
            raise HTTPException(status_code=500, detail="更新失败")
            
    except Exception as e:
        logger.error(f"更新知识失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{knowledge_id}")
async def delete_knowledge(knowledge_id: str):
    """删除知识"""
    try:
        success = await knowledge_base.delete_knowledge(knowledge_id)
        
        if success:
            return {"message": "删除成功"}
        else:
            raise HTTPException(status_code=500, detail="删除失败")
            
    except Exception as e:
        logger.error(f"删除知识失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., description="搜索关键词"),
    knowledge_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50)
):
    """搜索知识"""
    try:
        results = await knowledge_base.search_knowledge(
            query=q,
            knowledge_type=knowledge_type,
            limit=limit
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"搜索知识失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/for-agent/{agent_type}")
async def get_knowledge_for_agent(
    agent_type: str,
    context: str = Query(..., description="上下文内容"),
    limit: int = Query(5, ge=1, le=20)
):
    """为AI员工获取相关知识"""
    try:
        results = await knowledge_base.get_knowledge_for_agent(
            agent_type=agent_type,
            context=context,
            limit=limit
        )
        return {"knowledge": results}
    except Exception as e:
        logger.error(f"获取员工知识失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/answer")
async def get_answer(
    question: str = Query(..., description="问题")
):
    """为问题查找答案"""
    try:
        answer = await knowledge_base.get_answer_for_question(question)
        if answer:
            return {"answer": answer}
        else:
            return {"answer": None, "message": "未找到相关答案"}
    except Exception as e:
        logger.error(f"查找答案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics():
    """获取知识库统计"""
    try:
        return await knowledge_base.get_statistics()
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init-default")
async def init_default_knowledge():
    """初始化默认知识"""
    try:
        await knowledge_base.init_default_knowledge()
        return {"message": "初始化成功"}
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
