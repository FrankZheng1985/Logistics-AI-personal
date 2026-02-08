"""
记忆系统 - 记住老板的偏好、习惯、常用信息
Clauwdbot 的长期记忆能力
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import json

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class MemoryService:
    """用户偏好记忆服务"""
    
    # 偏好分类
    CATEGORIES = {
        "style": "文档/PPT风格偏好",
        "schedule": "日程习惯",
        "communication": "沟通偏好",
        "business": "业务关注点",
        "contacts": "常用联系人",
        "custom": "自定义信息"
    }
    
    async def remember(self, user_id: str, key: str, value: str, category: str = "custom") -> bool:
        """
        记住一条偏好信息
        
        Args:
            user_id: 用户ID
            key: 偏好键名（如 "ppt_style", "favorite_metric"）
            value: 偏好值
            category: 分类
        
        Returns:
            是否成功
        """
        try:
            async with AsyncSessionLocal() as db:
                # upsert: 存在则更新，不存在则插入
                await db.execute(
                    text("""
                        INSERT INTO user_preferences (user_id, pref_key, pref_value, category, updated_at)
                        VALUES (:user_id, :key, :value, :category, NOW())
                        ON CONFLICT (user_id, pref_key) 
                        DO UPDATE SET pref_value = :value, category = :category, updated_at = NOW()
                    """),
                    {"user_id": user_id, "key": key, "value": value, "category": category}
                )
                await db.commit()
            
            logger.info(f"[Memory] 记住偏好: {user_id}/{key} = {value[:50]}")
            return True
            
        except Exception as e:
            logger.error(f"[Memory] 记忆保存失败: {e}")
            return False
    
    async def recall(self, user_id: str, key: str) -> Optional[str]:
        """
        回忆一条偏好信息
        
        Args:
            user_id: 用户ID
            key: 偏好键名
        
        Returns:
            偏好值，不存在返回 None
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT pref_value FROM user_preferences
                        WHERE user_id = :user_id AND pref_key = :key
                    """),
                    {"user_id": user_id, "key": key}
                )
                row = result.fetchone()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"[Memory] 回忆失败: {e}")
            return None
    
    async def recall_all(self, user_id: str, category: str = None) -> Dict[str, str]:
        """
        回忆用户的所有偏好（或指定分类）
        
        Args:
            user_id: 用户ID
            category: 可选分类过滤
        
        Returns:
            {key: value} 字典
        """
        try:
            async with AsyncSessionLocal() as db:
                if category:
                    result = await db.execute(
                        text("""
                            SELECT pref_key, pref_value FROM user_preferences
                            WHERE user_id = :user_id AND category = :category
                            ORDER BY updated_at DESC
                        """),
                        {"user_id": user_id, "category": category}
                    )
                else:
                    result = await db.execute(
                        text("""
                            SELECT pref_key, pref_value FROM user_preferences
                            WHERE user_id = :user_id
                            ORDER BY updated_at DESC
                        """),
                        {"user_id": user_id}
                    )
                
                return {row[0]: row[1] for row in result.fetchall()}
                
        except Exception as e:
            logger.error(f"[Memory] 批量回忆失败: {e}")
            return {}
    
    async def forget(self, user_id: str, key: str) -> bool:
        """删除一条偏好"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("DELETE FROM user_preferences WHERE user_id = :user_id AND pref_key = :key"),
                    {"user_id": user_id, "key": key}
                )
                await db.commit()
            return True
        except Exception as e:
            logger.error(f"[Memory] 删除偏好失败: {e}")
            return False
    
    async def get_context_for_llm(self, user_id: str) -> str:
        """
        生成 LLM 上下文中的偏好信息（用于增强回复质量）
        
        Args:
            user_id: 用户ID
        
        Returns:
            格式化的偏好描述文本
        """
        prefs = await self.recall_all(user_id)
        
        if not prefs:
            return ""
        
        lines = ["关于这位老板的已知信息："]
        for key, value in prefs.items():
            readable_key = key.replace("_", " ")
            lines.append(f"- {readable_key}: {value}")
        
        return "\n".join(lines)


# 单例
memory_service = MemoryService()
