"""
邮件上下文服务 - Maria 的邮件记忆系统

让 Maria 能够记住最近处理过的邮件和附件，
当用户提到"那个合同"、"刚才的邮件"等时能够关联到正确的邮件。
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import json

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class EmailContextService:
    """邮件上下文服务 - Maria 的邮件短期记忆"""
    
    # 上下文保留时长（小时）
    CONTEXT_RETENTION_HOURS = 72  # 保留3天
    
    # 关键词映射：用户可能提到的词 -> 文档类型
    REFERENCE_KEYWORDS = {
        "合同": ["contract", "合同", "协议", "agreement"],
        "发票": ["invoice", "发票", "账单"],
        "报价": ["quote", "报价", "报价单", "quotation"],
        "提单": ["bl", "提单", "bill of lading", "海运单"],
        "报关单": ["customs", "报关", "清关"],
        "装箱单": ["packing", "装箱单"],
        "文档": ["doc", "document", "pdf", "文档", "文件"],
        "那个": None,  # 通用引用，取最近的
        "刚才": None,
        "之前": None,
        "再分析": None,
        "重新分析": None,
    }
    
    async def save_email_context(
        self,
        user_id: str,
        email_id: str,
        subject: str,
        from_address: str,
        from_name: str,
        attachment_name: str,
        attachment_content: str,
        analysis_result: str,
        doc_type: str = "general"
    ) -> bool:
        """
        保存邮件上下文
        
        Args:
            user_id: 用户ID
            email_id: 邮件唯一ID
            subject: 邮件主题
            from_address: 发件人邮箱
            from_name: 发件人名称
            attachment_name: 附件文件名
            attachment_content: 附件内容（截取前部分）
            analysis_result: AI分析结果
            doc_type: 文档类型 (contract/invoice/logistics/general)
        
        Returns:
            是否成功
        """
        try:
            async with AsyncSessionLocal() as db:
                # 检查表是否存在，不存在则创建
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS email_context (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(100) NOT NULL,
                        email_id VARCHAR(200) NOT NULL,
                        subject VARCHAR(500),
                        from_address VARCHAR(200),
                        from_name VARCHAR(200),
                        attachment_name VARCHAR(500),
                        attachment_content TEXT,
                        analysis_result TEXT,
                        doc_type VARCHAR(50) DEFAULT 'general',
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(user_id, email_id, attachment_name)
                    )
                """))
                
                # 插入或更新
                await db.execute(
                    text("""
                        INSERT INTO email_context 
                        (user_id, email_id, subject, from_address, from_name, 
                         attachment_name, attachment_content, analysis_result, doc_type, created_at)
                        VALUES (:user_id, :email_id, :subject, :from_address, :from_name,
                                :attachment_name, :attachment_content, :analysis_result, :doc_type, NOW())
                        ON CONFLICT (user_id, email_id, attachment_name) 
                        DO UPDATE SET 
                            analysis_result = :analysis_result,
                            created_at = NOW()
                    """),
                    {
                        "user_id": user_id,
                        "email_id": email_id,
                        "subject": subject,
                        "from_address": from_address,
                        "from_name": from_name,
                        "attachment_name": attachment_name,
                        "attachment_content": attachment_content[:10000],  # 限制长度
                        "analysis_result": analysis_result[:20000],  # 限制长度
                        "doc_type": doc_type
                    }
                )
                await db.commit()
            
            logger.info(f"[EmailContext] 保存邮件上下文: {attachment_name} (type={doc_type})")
            return True
            
        except Exception as e:
            logger.error(f"[EmailContext] 保存失败: {e}")
            return False
    
    async def get_recent_context(
        self,
        user_id: str,
        doc_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取最近的邮件上下文
        
        Args:
            user_id: 用户ID
            doc_type: 可选，过滤文档类型
            limit: 返回数量限制
        
        Returns:
            邮件上下文列表
        """
        try:
            async with AsyncSessionLocal() as db:
                if doc_type:
                    result = await db.execute(
                        text("""
                            SELECT email_id, subject, from_address, from_name, 
                                   attachment_name, attachment_content, analysis_result, 
                                   doc_type, created_at
                            FROM email_context
                            WHERE user_id = :user_id 
                              AND doc_type = :doc_type
                              AND created_at > NOW() - INTERVAL ':hours hours'
                            ORDER BY created_at DESC
                            LIMIT :limit
                        """.replace(':hours', str(self.CONTEXT_RETENTION_HOURS))),
                        {"user_id": user_id, "doc_type": doc_type, "limit": limit}
                    )
                else:
                    result = await db.execute(
                        text("""
                            SELECT email_id, subject, from_address, from_name, 
                                   attachment_name, attachment_content, analysis_result, 
                                   doc_type, created_at
                            FROM email_context
                            WHERE user_id = :user_id 
                              AND created_at > NOW() - INTERVAL ':hours hours'
                            ORDER BY created_at DESC
                            LIMIT :limit
                        """.replace(':hours', str(self.CONTEXT_RETENTION_HOURS))),
                        {"user_id": user_id, "limit": limit}
                    )
                
                rows = result.fetchall()
                contexts = []
                for row in rows:
                    contexts.append({
                        "email_id": row[0],
                        "subject": row[1],
                        "from_address": row[2],
                        "from_name": row[3],
                        "attachment_name": row[4],
                        "attachment_content": row[5],
                        "analysis_result": row[6],
                        "doc_type": row[7],
                        "created_at": row[8].isoformat() if row[8] else None
                    })
                
                return contexts
                
        except Exception as e:
            logger.error(f"[EmailContext] 获取上下文失败: {e}")
            return []
    
    async def find_referenced_email(
        self,
        user_id: str,
        user_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据用户消息找到被引用的邮件
        
        智能识别：
        - "那个合同" -> 找最近的合同类型附件
        - "刚才的报价" -> 找最近的报价类型附件
        - "再分析一次" -> 找最近处理的任意附件
        
        Args:
            user_id: 用户ID
            user_message: 用户消息内容
        
        Returns:
            被引用的邮件上下文，或 None
        """
        message_lower = user_message.lower()
        
        # 检测用户提到的文档类型
        detected_type = None
        for keyword, type_keywords in self.REFERENCE_KEYWORDS.items():
            if keyword in user_message:
                if type_keywords:  # 有明确的类型关键词
                    detected_type = keyword
                    break
        
        # 根据检测结果查询
        if detected_type == "合同":
            contexts = await self.get_recent_context(user_id, doc_type="contract", limit=1)
        elif detected_type == "发票":
            contexts = await self.get_recent_context(user_id, doc_type="invoice", limit=1)
        elif detected_type == "报价":
            contexts = await self.get_recent_context(user_id, doc_type="quote", limit=1)
        elif detected_type == "提单":
            contexts = await self.get_recent_context(user_id, doc_type="logistics", limit=1)
        elif detected_type == "报关单":
            contexts = await self.get_recent_context(user_id, doc_type="customs", limit=1)
        else:
            # 默认取最近的
            contexts = await self.get_recent_context(user_id, limit=1)
        
        if contexts:
            logger.info(f"[EmailContext] 找到引用邮件: {contexts[0]['attachment_name']}")
            return contexts[0]
        
        return None
    
    async def has_pending_reference(self, user_id: str, message: str) -> bool:
        """
        检查用户消息是否引用了之前的邮件
        
        Args:
            user_id: 用户ID
            message: 用户消息
        
        Returns:
            是否包含邮件引用
        """
        # 检查是否包含引用关键词
        reference_keywords = [
            "那个", "刚才", "之前", "再分析", "重新分析", "再看一次",
            "那份", "这个", "上次", "earlier", "previous", "again",
            "合同", "发票", "报价", "提单", "报关", "文档", "文件", "附件"
        ]
        
        for keyword in reference_keywords:
            if keyword in message:
                return True
        
        return False
    
    async def build_context_prompt(self, user_id: str, message: str) -> Optional[str]:
        """
        构建邮件上下文提示词
        
        当用户提到之前的邮件/附件时，自动注入上下文
        
        Args:
            user_id: 用户ID
            message: 用户消息
        
        Returns:
            上下文提示词，或 None（如果没有相关上下文）
        """
        # 检查是否需要上下文
        if not await self.has_pending_reference(user_id, message):
            return None
        
        # 查找被引用的邮件
        context = await self.find_referenced_email(user_id, message)
        if not context:
            return None
        
        # 构建上下文提示
        prompt = f"""
📧 **相关邮件上下文（自动注入）**

用户正在引用之前处理过的邮件附件：

- **邮件主题**: {context['subject']}
- **发件人**: {context['from_name']} <{context['from_address']}>
- **附件名称**: {context['attachment_name']}
- **文档类型**: {context['doc_type']}
- **处理时间**: {context['created_at']}

**附件内容摘要**:
{context['attachment_content'][:5000]}

**之前的分析结果**:
{context['analysis_result'][:5000]}

---
请基于以上上下文处理用户的请求。
"""
        return prompt
    
    async def cleanup_old_contexts(self, hours: int = None) -> int:
        """
        清理过期的邮件上下文
        
        Args:
            hours: 保留时长（小时），默认使用 CONTEXT_RETENTION_HOURS
        
        Returns:
            清理的记录数
        """
        hours = hours or self.CONTEXT_RETENTION_HOURS
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text(f"""
                        DELETE FROM email_context
                        WHERE created_at < NOW() - INTERVAL '{hours} hours'
                        RETURNING id
                    """)
                )
                deleted = len(result.fetchall())
                await db.commit()
            
            if deleted > 0:
                logger.info(f"[EmailContext] 清理过期上下文: {deleted} 条")
            
            return deleted
            
        except Exception as e:
            logger.error(f"[EmailContext] 清理失败: {e}")
            return 0


# 全局实例
email_context_service = EmailContextService()
