"""
VectorStoreService - 向量存储服务（基于PGVector）

提供语义搜索能力：
- 将对话历史自动嵌入为向量
- 基于语义相似度检索相关历史
- 与 MemoryService 联合实现 RAG（检索增强生成）

使用 OpenAI/DeepSeek 的 Embedding API 生成向量，
使用 PostgreSQL + pgvector 扩展存储和检索。
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import hashlib

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class VectorStoreService:
    """向量存储服务"""
    
    EMBEDDING_DIM = 1024  # Dashscope text-embedding-v3 最大支持 1024
    TABLE_NAME = "maria_memory_vectors"
    
    def __init__(self):
        self._initialized = False
        self._embedding_model = None
    
    async def initialize(self):
        """初始化：检查pgvector扩展和表"""
        if self._initialized:
            return
        
        try:
            async with AsyncSessionLocal() as db:
                # 启用 pgvector 扩展（如果不存在）
                await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                
                # 创建向量表（如果不存在）
                await db.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(100) NOT NULL,
                        content TEXT NOT NULL,
                        content_type VARCHAR(50) DEFAULT 'conversation',
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        embedding vector({self.EMBEDDING_DIM}),
                        content_hash VARCHAR(64) UNIQUE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """))
                
                # 创建 HNSW 索引（高性能近似最近邻）
                await db.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_embedding 
                    ON {self.TABLE_NAME} 
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """))
                
                # 创建 user_id 索引
                await db.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_user_id 
                    ON {self.TABLE_NAME} (user_id)
                """))
                
                await db.commit()
                
            self._initialized = True
            logger.info("[VectorStore] 初始化完成 (PGVector)")
            
        except Exception as e:
            logger.warning(f"[VectorStore] 初始化失败（向量搜索功能不可用）: {e}")
            # 不阻止启动，降级为无向量搜索
    
    async def _get_embedding(self, text_content: str) -> Optional[List[float]]:
        """获取文本的向量表示"""
        if not text_content or len(text_content.strip()) < 5:
            return None
        
        try:
            from app.core.config import settings
            import httpx
            
            # 优先用 DeepSeek Embedding，退回 Dashscope
            api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
            base_url = getattr(settings, 'DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
            model = "deepseek-chat"  # DeepSeek 不提供独立embedding API，我们用dashscope
            
            # 用通义千问的 text-embedding-v3
            dashscope_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
            if dashscope_key:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {dashscope_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "text-embedding-v3",
                            "input": text_content[:2000],  # 截断
                            "dimensions": self.EMBEDDING_DIM,
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        embedding = data["data"][0]["embedding"]
                        return embedding
                    else:
                        logger.warning(f"[VectorStore] Embedding API 返回 {response.status_code}: {response.text[:200]}")
                        return None
            
            logger.warning("[VectorStore] 没有可用的 Embedding API Key")
            return None
            
        except Exception as e:
            logger.warning(f"[VectorStore] 获取Embedding失败: {e}")
            return None
    
    def _content_hash(self, content: str) -> str:
        """生成内容哈希（用于去重）"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def store(self, user_id: str, content: str, 
                    content_type: str = "conversation",
                    metadata: Dict = None) -> bool:
        """
        存储一条带向量的记忆
        
        Args:
            user_id: 用户ID
            content: 文本内容
            content_type: 类型 (conversation/preference/task/note)
            metadata: 额外元数据
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            return False
        
        content_hash = self._content_hash(content)
        
        try:
            # 检查去重
            async with AsyncSessionLocal() as db:
                existing = await db.execute(
                    text(f"SELECT id FROM {self.TABLE_NAME} WHERE content_hash = :hash"),
                    {"hash": content_hash}
                )
                if existing.fetchone():
                    return True  # 已存在，跳过
            
            # 获取向量
            embedding = await self._get_embedding(content)
            if embedding is None:
                return False
            
            # 存储
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(f"""
                        INSERT INTO {self.TABLE_NAME} 
                        (user_id, content, content_type, metadata, embedding, content_hash)
                        VALUES (:user_id, :content, :content_type, :metadata, :embedding, :hash)
                        ON CONFLICT (content_hash) DO NOTHING
                    """),
                    {
                        "user_id": user_id,
                        "content": content,
                        "content_type": content_type,
                        "metadata": json.dumps(metadata or {}, ensure_ascii=False),
                        "embedding": str(embedding),  # pgvector 接受字符串格式
                        "hash": content_hash,
                    }
                )
                await db.commit()
            
            return True
            
        except Exception as e:
            logger.warning(f"[VectorStore] 存储失败: {e}")
            return False
    
    async def search(self, user_id: str, query: str, 
                     top_k: int = 5, 
                     content_type: str = None,
                     min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """
        语义搜索相关记忆
        
        Args:
            user_id: 用户ID
            query: 查询文本
            top_k: 返回条数
            content_type: 可选，过滤类型
            min_similarity: 最低相似度阈值
        
        Returns:
            [{"content": "...", "content_type": "...", "similarity": 0.85, "metadata": {}, "created_at": "..."}]
        """
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized:
            return []
        
        query_embedding = await self._get_embedding(query)
        if query_embedding is None:
            return []
        
        try:
            type_filter = "AND content_type = :content_type" if content_type else ""
            
            # 将向量转换为字符串格式，用于 CAST
            embedding_str = str(query_embedding)
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text(f"""
                        SELECT content, content_type, metadata, created_at,
                               1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                        FROM {self.TABLE_NAME}
                        WHERE user_id = :user_id
                        {type_filter}
                        AND 1 - (embedding <=> CAST(:query_embedding AS vector)) > :min_similarity
                        ORDER BY embedding <=> CAST(:query_embedding AS vector)
                        LIMIT :top_k
                    """),
                    {
                        "user_id": user_id,
                        "query_embedding": embedding_str,
                        "top_k": top_k,
                        "min_similarity": min_similarity,
                        **({"content_type": content_type} if content_type else {}),
                    }
                )
                
                rows = result.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "content": row[0],
                    "content_type": row[1],
                    "metadata": row[2] if isinstance(row[2], dict) else json.loads(row[2] or "{}"),
                    "created_at": str(row[3]),
                    "similarity": round(float(row[4]), 3),
                })
            
            return results
            
        except Exception as e:
            logger.warning(f"[VectorStore] 搜索失败: {e}")
            return []
    
    async def ingest_conversation(self, user_id: str, user_message: str, bot_response: str):
        """
        自动摄取一轮对话到向量库
        
        将对话压缩为一条记忆存储，而不是分开存 user/bot
        """
        if len(user_message) < 10 and len(bot_response) < 20:
            return  # 太短，不值得存
        
        combined = f"老板说：{user_message}\n助理回复：{bot_response[:300]}"
        
        metadata = {
            "user_message": user_message[:200],
            "bot_response_preview": bot_response[:200],
            "timestamp": datetime.now().isoformat(),
        }
        
        await self.store(
            user_id=user_id,
            content=combined,
            content_type="conversation",
            metadata=metadata,
        )
    
    async def get_relevant_context(self, user_id: str, current_message: str, top_k: int = 3) -> str:
        """
        获取与当前消息相关的历史上下文（RAG 检索步骤）
        
        Args:
            user_id: 用户ID
            current_message: 当前用户消息
            top_k: 返回条数
        
        Returns:
            格式化的上下文文本（直接注入system prompt）
        """
        results = await self.search(user_id, current_message, top_k=top_k)
        
        if not results:
            return ""
        
        lines = ["相关历史记忆（供参考）："]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. [{r['created_at'][:10]}] {r['content'][:200]}")
        
        return "\n".join(lines)
    
    async def get_stats(self, user_id: str = None) -> Dict[str, Any]:
        """获取向量库统计"""
        if not self._initialized:
            return {"initialized": False, "total": 0}
        
        try:
            async with AsyncSessionLocal() as db:
                if user_id:
                    result = await db.execute(
                        text(f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                else:
                    result = await db.execute(
                        text(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")
                    )
                count = result.fetchone()[0]
            
            return {"initialized": True, "total": count}
        except Exception:
            return {"initialized": False, "total": 0}


    async def sync_notion_knowledge(self, user_id: str = "system"):
        """
        从 Notion 关键文档同步知识到向量库
        
        定时任务（每晚23:00）自动执行：
        1. 读取 Notion 中"项目方案"和"知识库"分区的页面
        2. 提取每个页面的文本内容
        3. 向量化后存入向量库
        
        这样当老板在 Notion 更新了文档后，Maria 第二天就能在对话中引用
        """
        try:
            from app.skills.notion import get_notion_skill
            skill = await get_notion_skill()
            client = skill._get_client()
            
            # 搜索 Notion 中的关键分区
            target_sections = ["📋 项目方案", "📚 知识库"]
            synced_count = 0
            
            for section_title in target_sections:
                try:
                    search_result = client.search(
                        query=section_title,
                        filter={"property": "object", "value": "page"},
                        page_size=5,
                    )
                    
                    for item in search_result.get("results", []):
                        title = skill._extract_title(item)
                        if title != section_title:
                            continue
                        
                        section_id = item["id"]
                        
                        # 获取分区下的子页面
                        children = client.blocks.children.list(block_id=section_id, page_size=20)
                        
                        for block in children.get("results", []):
                            if block.get("type") != "child_page":
                                continue
                            
                            page_id = block["id"]
                            page_title = block.get("child_page", {}).get("title", "")
                            
                            if not page_title:
                                continue
                            
                            # 读取页面内容
                            page_blocks = client.blocks.children.list(block_id=page_id, page_size=50)
                            text_parts = []
                            
                            for pb in page_blocks.get("results", []):
                                rich_texts = []
                                block_type = pb.get("type", "")
                                block_data = pb.get(block_type, {})
                                
                                if isinstance(block_data, dict):
                                    for rt in block_data.get("rich_text", []):
                                        plain = rt.get("plain_text", "")
                                        if plain:
                                            rich_texts.append(plain)
                                
                                if rich_texts:
                                    text_parts.append(" ".join(rich_texts))
                            
                            if not text_parts:
                                continue
                            
                            # 拼接为摘要
                            full_text = f"Notion文档「{page_title}」内容摘要：\n" + "\n".join(text_parts[:30])
                            
                            if len(full_text) > 2000:
                                full_text = full_text[:2000]
                            
                            # 存入向量库
                            stored = await self.store(
                                user_id=user_id,
                                content=full_text,
                                content_type="notion_knowledge",
                                metadata={
                                    "source": "notion",
                                    "page_title": page_title,
                                    "section": section_title,
                                    "synced_at": datetime.now().isoformat(),
                                }
                            )
                            
                            if stored:
                                synced_count += 1
                            
                except Exception as e:
                    logger.warning(f"[VectorStore] 同步分区 {section_title} 失败: {e}")
                    continue
            
            logger.info(f"[VectorStore] Notion知识库同步完成: {synced_count} 个文档")
            return synced_count
            
        except Exception as e:
            logger.warning(f"[VectorStore] Notion知识库同步失败: {e}")
            return 0


# 单例
vector_store = VectorStoreService()
