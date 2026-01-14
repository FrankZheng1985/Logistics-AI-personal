"""
知识库服务
负责：知识库管理、知识检索、知识应用
"""
from typing import Dict, Any, List, Optional
from loguru import logger

from app.models.database import AsyncSessionLocal


class KnowledgeService:
    """知识库服务"""
    
    # 知识分类
    CATEGORIES = {
        "clearance": "清关政策",
        "transit": "时效航线",
        "pricing": "报价策略",
        "risk": "风险管理",
        "faq": "常见问题",
        "terminology": "行业术语",
        "sales": "销售话术",
        "case": "案例经验"
    }
    
    # 经验级别
    EXPERIENCE_LEVELS = {
        "beginner": "入门",
        "intermediate": "熟练",
        "expert": "专家"
    }
    
    async def search_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """搜索知识库"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                # 构建查询
                sql = """
                    SELECT id, category, title, content, summary, 
                           applicable_routes, applicable_countries,
                           experience_level, keywords
                    FROM logistics_knowledge
                    WHERE is_verified = TRUE
                """
                params = {"limit": limit}
                
                if category:
                    sql += " AND category = :category"
                    params["category"] = category
                
                # 简单的关键词匹配（可以后续升级为全文搜索）
                sql += " AND (title ILIKE :query OR content ILIKE :query OR :query = ANY(keywords))"
                params["query"] = f"%{query}%"
                
                sql += " ORDER BY usage_count DESC LIMIT :limit"
                
                result = await db.execute(text(sql), params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "category": row[1],
                        "title": row[2],
                        "content": row[3],
                        "summary": row[4],
                        "applicable_routes": row[5],
                        "applicable_countries": row[6],
                        "experience_level": row[7],
                        "keywords": row[8]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"搜索知识库失败: {e}")
            return []
    
    async def get_knowledge_by_category(
        self,
        category: str,
        experience_level: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """按分类获取知识"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                sql = """
                    SELECT id, title, content, summary, experience_level
                    FROM logistics_knowledge
                    WHERE category = :category AND is_verified = TRUE
                """
                params = {"category": category, "limit": limit}
                
                if experience_level:
                    sql += " AND experience_level = :level"
                    params["level"] = experience_level
                
                sql += " ORDER BY usage_count DESC LIMIT :limit"
                
                result = await db.execute(text(sql), params)
                rows = result.fetchall()
                
                return [
                    {
                        "id": str(row[0]),
                        "title": row[1],
                        "content": row[2],
                        "summary": row[3],
                        "experience_level": row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取知识失败: {e}")
            return []
    
    async def get_route_knowledge(
        self,
        from_location: str,
        to_location: str
    ) -> List[Dict[str, Any]]:
        """获取特定航线的知识"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                result = await db.execute(
                    text("""
                        SELECT id, category, title, content, summary
                        FROM logistics_knowledge
                        WHERE is_verified = TRUE
                        AND (:from_loc = ANY(applicable_routes) OR :to_loc = ANY(applicable_routes))
                        ORDER BY usage_count DESC
                        LIMIT 5
                    """),
                    {"from_loc": from_location, "to_loc": to_location}
                )
                
                rows = result.fetchall()
                return [
                    {
                        "id": str(row[0]),
                        "category": row[1],
                        "title": row[2],
                        "content": row[3],
                        "summary": row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"获取航线知识失败: {e}")
            return []
    
    async def add_knowledge(
        self,
        category: str,
        title: str,
        content: str,
        summary: Optional[str] = None,
        applicable_routes: Optional[List[str]] = None,
        applicable_countries: Optional[List[str]] = None,
        experience_level: str = "intermediate",
        keywords: Optional[List[str]] = None,
        source: Optional[str] = None
    ) -> Optional[str]:
        """添加知识"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                import uuid
                
                knowledge_id = str(uuid.uuid4())
                
                await db.execute(
                    text("""
                        INSERT INTO logistics_knowledge
                        (id, category, title, content, summary, applicable_routes,
                         applicable_countries, experience_level, keywords, source,
                         is_verified, created_at)
                        VALUES (:id, :category, :title, :content, :summary, :routes,
                                :countries, :level, :keywords, :source, FALSE, NOW())
                    """),
                    {
                        "id": knowledge_id,
                        "category": category,
                        "title": title,
                        "content": content,
                        "summary": summary,
                        "routes": applicable_routes or [],
                        "countries": applicable_countries or [],
                        "level": experience_level,
                        "keywords": keywords or [],
                        "source": source
                    }
                )
                await db.commit()
                
                logger.info(f"知识已添加: {title}")
                return knowledge_id
        except Exception as e:
            logger.error(f"添加知识失败: {e}")
            return None
    
    async def record_usage(self, knowledge_id: str):
        """记录知识使用"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                await db.execute(
                    text("""
                        UPDATE logistics_knowledge 
                        SET usage_count = usage_count + 1, 
                            last_used_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": knowledge_id}
                )
                await db.commit()
        except Exception as e:
            logger.error(f"记录使用失败: {e}")
    
    async def get_expert_knowledge_context(
        self,
        agent_type: str = "general"
    ) -> str:
        """获取专家级知识上下文，供AI员工使用"""
        from app.core.prompts.logistics_expert import (
            LOGISTICS_EXPERT_BASE_PROMPT,
            SEA_FREIGHT_KNOWLEDGE,
            AIR_FREIGHT_KNOWLEDGE,
            CUSTOMS_CLEARANCE_KNOWLEDGE,
            CUSTOMER_PAIN_POINTS_SOLUTIONS,
            LOGISTICS_TERMINOLOGY
        )
        
        # 根据AI员工类型返回相关知识
        context_parts = [LOGISTICS_EXPERT_BASE_PROMPT]
        
        if agent_type in ["sales", "follow", "analyst"]:
            context_parts.append(CUSTOMER_PAIN_POINTS_SOLUTIONS)
            context_parts.append(LOGISTICS_TERMINOLOGY)
        
        if agent_type in ["copywriter", "video_creator"]:
            context_parts.append(SEA_FREIGHT_KNOWLEDGE[:1000])  # 精简版
            context_parts.append(AIR_FREIGHT_KNOWLEDGE[:1000])
        
        if agent_type == "sales":
            from app.core.prompts.logistics_expert import SALES_SCRIPTS
            context_parts.append(SALES_SCRIPTS)
        
        if agent_type == "lead_hunter":
            context_parts.append(CUSTOMS_CLEARANCE_KNOWLEDGE[:1000])
        
        return "\n\n".join(context_parts)
    
    async def get_faq_answer(self, question: str) -> Optional[Dict[str, Any]]:
        """获取FAQ答案"""
        results = await self.search_knowledge(question, category="faq", limit=1)
        return results[0] if results else None


# 创建服务实例
knowledge_service = KnowledgeService()
