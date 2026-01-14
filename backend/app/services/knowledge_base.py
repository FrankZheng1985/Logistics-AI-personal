"""
知识库服务
AI员工共享知识库系统
支持知识的存储、检索、更新
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy import text

from app.models.database import async_session_maker
from app.core.config import settings


# 知识类型定义
KNOWLEDGE_TYPES = {
    "clearance_exp": {
        "name": "清关经验",
        "description": "欧洲各国清关流程、注意事项、常见问题"
    },
    "price_ref": {
        "name": "运价参考",
        "description": "欧洲各线路运价、清关费用、派送费率"
    },
    "policy": {
        "name": "政策法规",
        "description": "欧盟/各国海关政策、VAT规定、合规要求"
    },
    "faq": {
        "name": "常见问题",
        "description": "客户常问问题及标准回答"
    },
    "pain_point": {
        "name": "客户痛点",
        "description": "客户关注的痛点和解决方案"
    },
    "market_intel": {
        "name": "市场情报",
        "description": "行业动态、竞品信息、市场趋势"
    },
    "case_study": {
        "name": "成功案例",
        "description": "客户成功案例和解决方案"
    },
    "sales_skill": {
        "name": "销售技巧",
        "description": "话术模板、异议处理、成交技巧"
    }
}


class KnowledgeBaseService:
    """知识库服务"""
    
    def __init__(self):
        pass
    
    async def add_knowledge(
        self,
        content: str,
        knowledge_type: str,
        source: str = "manual",
        source_id: Optional[str] = None,
        tags: List[str] = None,
        is_verified: bool = False
    ) -> Optional[str]:
        """
        添加知识
        
        Args:
            content: 知识内容
            knowledge_type: 知识类型
            source: 来源 (wechat_group/market_intel/manual)
            source_id: 来源记录ID
            tags: 标签列表
            is_verified: 是否已验证
        
        Returns:
            知识ID
        """
        if knowledge_type not in KNOWLEDGE_TYPES:
            logger.warning(f"未知的知识类型: {knowledge_type}")
            knowledge_type = "faq"
        
        try:
            async with async_session_maker() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO knowledge_base 
                        (content, knowledge_type, source, source_id, tags, is_verified, created_at, updated_at)
                        VALUES (:content, :type, :source, :source_id, :tags, :verified, NOW(), NOW())
                        RETURNING id
                    """),
                    {
                        "content": content,
                        "type": knowledge_type,
                        "source": source,
                        "source_id": source_id,
                        "tags": tags or [],
                        "verified": is_verified
                    }
                )
                knowledge_id = result.fetchone()[0]
                await db.commit()
                
                logger.info(f"📚 添加知识: [{knowledge_type}] {content[:50]}...")
                return str(knowledge_id)
                
        except Exception as e:
            logger.error(f"添加知识失败: {e}")
            return None
    
    async def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        tags: List[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索知识
        
        Args:
            query: 搜索关键词
            knowledge_type: 限定知识类型
            tags: 限定标签
            limit: 返回数量
        
        Returns:
            匹配的知识列表
        """
        try:
            async with async_session_maker() as db:
                # 构建查询
                sql = """
                    SELECT id, content, knowledge_type, source, tags, 
                           is_verified, usage_count, created_at
                    FROM knowledge_base
                    WHERE content ILIKE :query
                """
                params = {"query": f"%{query}%", "limit": limit}
                
                if knowledge_type:
                    sql += " AND knowledge_type = :type"
                    params["type"] = knowledge_type
                
                if tags:
                    sql += " AND tags && :tags"
                    params["tags"] = tags
                
                sql += " ORDER BY is_verified DESC, usage_count DESC LIMIT :limit"
                
                result = await db.execute(text(sql), params)
                rows = result.fetchall()
                
                return [
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
                
        except Exception as e:
            logger.error(f"搜索知识失败: {e}")
            return []
    
    async def get_knowledge_for_agent(
        self,
        agent_type: str,
        context: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        为AI员工获取相关知识
        
        Args:
            agent_type: AI员工类型
            context: 上下文（对话内容、任务描述等）
            limit: 返回数量
        
        Returns:
            相关知识列表
        """
        # 根据员工类型确定优先知识类型
        type_priority = {
            "sales": ["faq", "sales_skill", "price_ref", "case_study"],
            "follow": ["faq", "sales_skill", "pain_point"],
            "copywriter": ["case_study", "pain_point", "policy"],
            "analyst": ["market_intel", "price_ref", "policy"],
            "analyst2": ["market_intel", "policy", "clearance_exp"]
        }
        
        preferred_types = type_priority.get(agent_type, list(KNOWLEDGE_TYPES.keys()))
        
        try:
            async with async_session_maker() as db:
                # 先按类型优先级搜索
                all_results = []
                
                for knowledge_type in preferred_types:
                    results = await self.search_knowledge(
                        query=context[:100],  # 使用上下文的前100字符作为搜索词
                        knowledge_type=knowledge_type,
                        limit=2
                    )
                    all_results.extend(results)
                    
                    if len(all_results) >= limit:
                        break
                
                # 记录使用
                for item in all_results[:limit]:
                    await db.execute(
                        text("""
                            UPDATE knowledge_base
                            SET usage_count = usage_count + 1
                            WHERE id = :id
                        """),
                        {"id": item["id"]}
                    )
                await db.commit()
                
                return all_results[:limit]
                
        except Exception as e:
            logger.error(f"获取员工知识失败: {e}")
            return []
    
    async def get_answer_for_question(
        self,
        question: str
    ) -> Optional[Dict[str, Any]]:
        """
        为问题查找答案（用于小销回答客户）
        
        Args:
            question: 客户问题
        
        Returns:
            最匹配的知识/答案
        """
        # 关键词匹配
        keywords = self._extract_keywords(question)
        
        results = []
        for kw in keywords:
            matched = await self.search_knowledge(
                query=kw,
                knowledge_type="faq",
                limit=3
            )
            results.extend(matched)
        
        # 去重并按使用次数排序
        seen_ids = set()
        unique_results = []
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_results.append(r)
        
        unique_results.sort(key=lambda x: x["usage_count"], reverse=True)
        
        return unique_results[0] if unique_results else None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（可以后续用更复杂的NLP）
        stop_words = {"的", "是", "在", "有", "和", "了", "吗", "呢", "啊", "什么", "怎么", "如何"}
        
        # 按标点分割
        import re
        words = re.split(r'[，。？！、\s]+', text)
        
        # 过滤停用词和太短的词
        keywords = [w for w in words if w and len(w) > 1 and w not in stop_words]
        
        return keywords[:5]  # 最多5个关键词
    
    async def update_knowledge(
        self,
        knowledge_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_verified: Optional[bool] = None
    ) -> bool:
        """更新知识"""
        try:
            async with async_session_maker() as db:
                updates = ["updated_at = NOW()"]
                params = {"id": knowledge_id}
                
                if content is not None:
                    updates.append("content = :content")
                    params["content"] = content
                
                if tags is not None:
                    updates.append("tags = :tags")
                    params["tags"] = tags
                
                if is_verified is not None:
                    updates.append("is_verified = :verified")
                    params["verified"] = is_verified
                
                sql = f"UPDATE knowledge_base SET {', '.join(updates)} WHERE id = :id"
                await db.execute(text(sql), params)
                await db.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"更新知识失败: {e}")
            return False
    
    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识"""
        try:
            async with async_session_maker() as db:
                await db.execute(
                    text("DELETE FROM knowledge_base WHERE id = :id"),
                    {"id": knowledge_id}
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"删除知识失败: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计"""
        try:
            async with async_session_maker() as db:
                # 总量统计
                result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE is_verified = true) as verified,
                            SUM(usage_count) as total_usage
                        FROM knowledge_base
                    """)
                )
                total_stats = result.fetchone()
                
                # 按类型统计
                result = await db.execute(
                    text("""
                        SELECT knowledge_type, COUNT(*) as count
                        FROM knowledge_base
                        GROUP BY knowledge_type
                        ORDER BY count DESC
                    """)
                )
                type_stats = result.fetchall()
                
                # 按来源统计
                result = await db.execute(
                    text("""
                        SELECT source, COUNT(*) as count
                        FROM knowledge_base
                        GROUP BY source
                        ORDER BY count DESC
                    """)
                )
                source_stats = result.fetchall()
                
                # 热门知识
                result = await db.execute(
                    text("""
                        SELECT id, content, knowledge_type, usage_count
                        FROM knowledge_base
                        ORDER BY usage_count DESC
                        LIMIT 10
                    """)
                )
                hot_knowledge = result.fetchall()
                
                return {
                    "total": {
                        "count": total_stats[0] if total_stats else 0,
                        "verified": total_stats[1] if total_stats else 0,
                        "total_usage": total_stats[2] if total_stats else 0
                    },
                    "by_type": [
                        {
                            "type": row[0],
                            "type_name": KNOWLEDGE_TYPES.get(row[0], {}).get("name", row[0]),
                            "count": row[1]
                        }
                        for row in type_stats
                    ],
                    "by_source": [
                        {"source": row[0], "count": row[1]}
                        for row in source_stats
                    ],
                    "hot_knowledge": [
                        {
                            "id": str(row[0]),
                            "content": row[1][:100],
                            "type": row[2],
                            "usage_count": row[3]
                        }
                        for row in hot_knowledge
                    ]
                }
                
        except Exception as e:
            logger.error(f"获取知识库统计失败: {e}")
            return {}
    
    async def init_default_knowledge(self):
        """初始化默认知识"""
        default_knowledge = [
            # FAQ
            {
                "content": "欧洲清关一般需要1-3个工作日，具体时间取决于货物类型和海关查验情况。",
                "type": "faq",
                "tags": ["清关", "时效", "欧洲"]
            },
            {
                "content": "VAT是增值税，在欧盟国家进口时需要缴纳。一般为货值的19-23%，具体税率因国家而异。",
                "type": "faq",
                "tags": ["VAT", "税率", "欧盟"]
            },
            {
                "content": "德国清关需要提供发票、装箱单、原产地证明。如果是特殊商品还需要相关资质证书。",
                "type": "faq",
                "tags": ["德国", "清关", "资料"]
            },
            # 清关经验
            {
                "content": "法国海关对产品描述要求严格，务必使用准确的HS编码，避免因编码错误导致查验或罚款。",
                "type": "clearance_exp",
                "tags": ["法国", "HS编码", "注意事项"]
            },
            {
                "content": "英国脱欧后需要单独的清关流程，进入欧盟需要再次清关，建议客户规划好物流路线。",
                "type": "clearance_exp",
                "tags": ["英国", "脱欧", "清关"]
            },
            # 销售技巧
            {
                "content": "当客户询问价格时，先了解货物类型、重量、目的地，然后给出包含清关和派送的整体方案，而不是单纯报运费。",
                "type": "sales_skill",
                "tags": ["报价", "技巧"]
            },
            {
                "content": "客户犹豫时，可以分享成功案例，展示我们在欧洲清关的专业能力和时效保障。",
                "type": "sales_skill",
                "tags": ["成交", "案例"]
            }
        ]
        
        for item in default_knowledge:
            await self.add_knowledge(
                content=item["content"],
                knowledge_type=item["type"],
                source="system",
                tags=item["tags"],
                is_verified=True
            )
        
        logger.info(f"📚 初始化 {len(default_knowledge)} 条默认知识")


# 创建单例
knowledge_base = KnowledgeBaseService()
