"""
记忆系统 - 记住老板的偏好、习惯、常用信息
Clauwdbot 的长期记忆 + 自我学习能力
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import json
import re

from app.models.database import AsyncSessionLocal
from sqlalchemy import text
from app.core.llm import chat_completion


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
    
    # ==================== 自我学习能力 ====================
    
    async def auto_learn(self, user_id: str, message: str, response: str, intent_type: str) -> None:
        """
        对话后自动学习：从对话中提取可记忆的偏好/习惯/信息
        
        这个方法在每次对话结束后异步调用，不影响主流程速度。
        
        Args:
            user_id: 用户ID
            message: 用户消息
            response: Clauwdbot的回复
            intent_type: 意图类型
        """
        try:
            # 太短的对话不值得分析
            if len(message) < 5:
                return
            
            learn_prompt = f"""你是一个学习引擎。请分析以下老板和AI助理的对话，提取值得长期记住的信息。

老板说：{message}
助理回复：{response}
对话类型：{intent_type}

请判断这段对话中是否包含以下任何值得记住的信息：
1. 老板的偏好（如"喜欢简洁"、"喜欢详细数据"、"PPT要XX风格"）
2. 老板的习惯（如"下午通常开会"、"周一喜欢看周报"）
3. 业务信息（如"重点关注德国线"、"张总是大客户"）
4. 纠正/不满（如老板说"不对"、"不是这样"、"太长了"、"太机器"，说明需要调整行为）
5. 联系人信息（如提到的人名、公司名、关系）

如果有值得记住的，返回JSON：
{{"learn": true, "items": [{{"key": "偏好键名_用英文", "value": "偏好内容_用中文", "category": "style/schedule/communication/business/contacts/correction"}}]}}

如果没什么值得记住的，返回：
{{"learn": false}}

只返回JSON，不要其他内容。注意：日常的查询（如"今天有什么安排"）通常不需要记忆。只记真正有价值的信息。"""

            result = await chat_completion(
                messages=[{"role": "user", "content": learn_prompt}],
                temperature=0.2,
                max_tokens=500
            )
            
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if not json_match:
                return
            
            learn_data = json.loads(json_match.group())
            
            if not learn_data.get("learn"):
                return
            
            # 保存学到的信息
            items = learn_data.get("items", [])
            for item in items[:5]:  # 每次最多学5条，防止过度
                key = item.get("key", "").strip()
                value = item.get("value", "").strip()
                category = item.get("category", "custom")
                
                if key and value:
                    await self.remember(user_id, key, value, category)
                    logger.info(f"[Memory] 自动学习: {key} = {value}")
            
        except Exception as e:
            # 学习失败不影响主流程
            logger.warning(f"[Memory] 自动学习失败（不影响主流程）: {e}")
    
    async def detect_correction(self, message: str) -> bool:
        """
        检测用户消息是否是在纠正/表达不满
        
        Args:
            message: 用户消息
        
        Returns:
            是否是纠正
        """
        correction_keywords = [
            "不对", "不是", "错了", "不要", "别", "太长", "太短",
            "太机器", "不够", "不好", "换一个", "重新", "重来",
            "不是这样", "我说的是", "不是我要的", "差评", "不行"
        ]
        
        message_lower = message.lower()
        return any(kw in message_lower for kw in correction_keywords)
    
    async def learn_from_correction(self, user_id: str, original_message: str, correction_message: str) -> None:
        """
        从纠正中学习：当老板说"不对/不好"时，分析并记住
        
        Args:
            user_id: 用户ID
            original_message: 触发纠正的原始上下文
            correction_message: 老板的纠正消息
        """
        try:
            learn_prompt = f"""老板对AI助理的回复不满意，发了纠正消息。请分析老板想要什么，提取需要记住的教训。

老板的纠正：{correction_message}

请返回JSON格式：
{{"key": "correction_英文描述", "value": "老板希望的行为/风格_用中文描述", "category": "correction"}}

例如：
老板说"太长了" -> {{"key": "correction_response_length", "value": "老板喜欢简短的回复，不要太啰嗦", "category": "correction"}}
老板说"太机器了" -> {{"key": "correction_tone", "value": "老板希望回复更自然、口语化，不要像机器人", "category": "correction"}}

只返回JSON。"""

            result = await chat_completion(
                messages=[{"role": "user", "content": learn_prompt}],
                temperature=0.2,
                max_tokens=300
            )
            
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                key = data.get("key", "")
                value = data.get("value", "")
                if key and value:
                    await self.remember(user_id, key, value, "correction")
                    logger.info(f"[Memory] 纠错学习: {key} = {value}")
        
        except Exception as e:
            logger.warning(f"[Memory] 纠错学习失败: {e}")


# 单例
memory_service = MemoryService()
