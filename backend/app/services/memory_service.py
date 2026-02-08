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
        "custom": "自定义信息",
        "correction": "纠错教训",
        "action_rule": "行动准则（强制执行）",
    }
    
    # 对话分类：判断是否值得学习的关键词
    SKIP_KEYWORDS = [
        "你好", "在吗", "嗯", "好的", "谢谢", "ok", "收到",
        "哈哈", "呵呵", "哦", "嗯嗯", "好", "行",
    ]
    
    # 隐式负面反馈模式（用户重发、追问、不耐烦）
    IMPLICIT_NEGATIVE_PATTERNS = [
        "我刚才说的是", "你没听懂", "再说一遍", "不是这个意思",
        "怎么还没", "搞什么", "到底", "能不能", "为什么不",
        "我要的是", "你理解错了", "答非所问",
    ]
    
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
        生成 LLM 上下文中的偏好和行动准则（分层注入）
        
        Returns:
            格式化的上下文文本（偏好 + 行动准则分开展示）
        """
        prefs = await self.recall_all(user_id)
        
        if not prefs:
            return ""
        
        # 分层：行动准则 vs 普通偏好
        rules = {}
        preferences = {}
        for key, value in prefs.items():
            if key.startswith("rule_") or key.startswith("correction_"):
                rules[key] = value
            else:
                preferences[key] = value
        
        lines = []
        
        # 行动准则优先展示（权重更高）
        if rules:
            lines.append("你必须遵守的行动准则（从过往教训中学到的，务必执行）：")
            for key, value in list(rules.items())[:10]:  # 最多10条
                lines.append(f"- {value}")
        
        # 普通偏好
        if preferences:
            lines.append("\n关于老板的已知偏好：")
            for key, value in list(preferences.items())[:15]:  # 最多15条
                readable_key = key.replace("_", " ")
                lines.append(f"- {readable_key}: {value}")
        
        return "\n".join(lines)
    
    async def get_action_rules(self, user_id: str) -> List[str]:
        """获取所有行动准则（用于特定场景的强制注入）"""
        rules = await self.recall_all(user_id, category="action_rule")
        corrections = await self.recall_all(user_id, category="correction")
        
        all_rules = []
        for value in list(rules.values())[:10]:
            all_rules.append(value)
        for value in list(corrections.values())[:10]:
            all_rules.append(value)
        
        return all_rules
    
    # ==================== 自我学习能力（增强版） ====================
    
    def _is_worth_learning(self, message: str) -> bool:
        """判断对话是否值得学习（降噪）"""
        msg = message.strip()
        
        # 太短的消息
        if len(msg) < 5:
            return False
        
        # 纯闲聊跳过
        if msg in self.SKIP_KEYWORDS:
            return False
        
        return True
    
    async def auto_learn(self, user_id: str, message: str, response: str, intent_type: str = "") -> None:
        """
        对话后自动学习（增强版）：
        1. 提取偏好/习惯/业务信息
        2. 生成行动准则（从纠错中提炼具体规则）
        3. 记录到 Notion 成长日志
        """
        try:
            if not self._is_worth_learning(message):
                return
            
            # 检测是否有隐式负面反馈
            has_implicit_negative = any(p in message for p in self.IMPLICIT_NEGATIVE_PATTERNS)
            
            learn_prompt = f"""你是一个AI助理的学习引擎。请分析以下老板和AI助理的对话，提取值得长期记住的信息。

老板说：{message}
助理回复：{response[:300]}

请从以下维度分析：

1. **偏好/习惯**：老板的风格偏好、时间习惯、沟通方式
2. **业务知识**：项目信息、客户信息、业务规则、行业知识
3. **行动准则**（最重要）：如果老板表达了不满、纠正、要求改变，必须生成一条具体的行动准则
   - 行动准则格式："在做[场景]时，必须[具体行为]，禁止[错误行为]"
   - 例："在汇报任务时，必须说清楚做了什么和结果是什么，禁止只说'处理好了'"
4. **联系人**：新提到的人名、公司名、关系

{"'⚠️ 注意：老板的消息中疑似包含不满或纠正，请特别关注并生成行动准则。'" if has_implicit_negative else ''}

返回JSON：
{{"learn": true, "items": [{{"key": "英文键名", "value": "中文内容", "category": "style/schedule/communication/business/contacts/action_rule/correction"}}]}}

或者没有值得记忆的：
{{"learn": false}}

只返回JSON。日常查询（如"看邮件"、"今天日程"）不需要记忆。"""

            result = await chat_completion(
                messages=[{"role": "user", "content": learn_prompt}],
                temperature=0.2,
                max_tokens=600
            )
            
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if not json_match:
                return
            
            learn_data = json.loads(json_match.group())
            
            if not learn_data.get("learn"):
                return
            
            # 保存学到的信息
            items = learn_data.get("items", [])
            growth_entries = []
            
            for item in items[:5]:
                key = item.get("key", "").strip()
                value = item.get("value", "").strip()
                category = item.get("category", "custom")
                
                if not key or not value:
                    continue
                
                # 行动准则加前缀，方便识别
                if category == "action_rule" and not key.startswith("rule_"):
                    key = f"rule_{key}"
                
                await self.remember(user_id, key, value, category)
                logger.info(f"[Memory] 自动学习: [{category}] {key} = {value}")
                
                # 收集成长日志条目
                type_label = {
                    "action_rule": "行动准则",
                    "correction": "纠错教训",
                    "business": "业务知识",
                    "style": "偏好学习",
                    "contacts": "人脉信息",
                }.get(category, "学习")
                growth_entries.append(f"[{type_label}] {value}")
            
            # 写入 Notion 成长日志
            if growth_entries:
                await self._write_growth_log(growth_entries, message[:50])
            
        except Exception as e:
            logger.warning(f"[Memory] 自动学习失败（不影响主流程）: {e}")
    
    async def detect_correction(self, message: str) -> bool:
        """
        检测用户消息是否是在纠正/表达不满（增强版，含隐式反馈）
        """
        correction_keywords = [
            "不对", "不是", "错了", "不要", "别", "太长", "太短",
            "太机器", "不够", "不好", "换一个", "重新", "重来",
            "不是这样", "我说的是", "不是我要的", "差评", "不行",
        ]
        
        message_lower = message.lower()
        
        # 显式纠错
        if any(kw in message_lower for kw in correction_keywords):
            return True
        
        # 隐式负面反馈
        if any(p in message_lower for p in self.IMPLICIT_NEGATIVE_PATTERNS):
            return True
        
        return False
    
    async def learn_from_correction(self, user_id: str, original_message: str, correction_message: str) -> None:
        """
        从纠正中学习（增强版）：生成行动准则 + 记录成长日志
        """
        try:
            learn_prompt = f"""老板对AI助理不满意，发了纠正消息。请分析并生成一条具体的行动准则。

老板的纠正：{correction_message}
之前的上下文：{original_message[:200]}

请返回JSON，包含两个字段：
1. 一条行动准则（具体、可执行的规则）
2. 一条纠错记录

格式：
{{"rule_key": "rule_英文描述", "rule_value": "在做[场景]时，必须[行为]，禁止[错误行为]", "correction_key": "correction_英文描述", "correction_value": "老板不满意的原因和期望"}}

例如：
老板说"你没有告诉我具体做了什么":
{{"rule_key": "rule_report_detail", "rule_value": "在汇报任务结果时，必须说清楚具体做了什么操作、结果是什么、下一步是什么，禁止只说处理好了", "correction_key": "correction_vague_report", "correction_value": "老板不满意模糊的汇报，要求每次汇报都有具体内容"}}

只返回JSON。"""

            result = await chat_completion(
                messages=[{"role": "user", "content": learn_prompt}],
                temperature=0.2,
                max_tokens=400
            )
            
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if not json_match:
                return
            
            data = json.loads(json_match.group())
            
            growth_entries = []
            
            # 保存行动准则
            rule_key = data.get("rule_key", "")
            rule_value = data.get("rule_value", "")
            if rule_key and rule_value:
                await self.remember(user_id, rule_key, rule_value, "action_rule")
                logger.info(f"[Memory] 行动准则: {rule_key} = {rule_value}")
                growth_entries.append(f"[行动准则] {rule_value}")
            
            # 保存纠错记录
            corr_key = data.get("correction_key", "")
            corr_value = data.get("correction_value", "")
            if corr_key and corr_value:
                await self.remember(user_id, corr_key, corr_value, "correction")
                logger.info(f"[Memory] 纠错学习: {corr_key} = {corr_value}")
                growth_entries.append(f"[纠错教训] {corr_value}")
            
            # 写入成长日志
            if growth_entries:
                await self._write_growth_log(
                    growth_entries,
                    f"老板纠正: {correction_message[:30]}"
                )
        
        except Exception as e:
            logger.warning(f"[Memory] 纠错学习失败: {e}")
    
    # ==================== Notion 成长日志 ====================
    
    async def _write_growth_log(self, entries: List[str], trigger: str = ""):
        """
        将学习成果写入 Notion 成长日志
        
        格式：在"成长日志"页面追加当天的学习记录
        """
        try:
            from app.skills.notion import get_notion_skill
            
            skill = await get_notion_skill()
            now = datetime.now()
            time_str = now.strftime("%H:%M")
            date_str = now.strftime("%Y-%m-%d")
            
            # 构建 Markdown 内容
            lines = [f"### {time_str} - {trigger}"]
            for entry in entries:
                lines.append(f"- {entry}")
            lines.append("")
            
            content = "\n".join(lines)
            
            # 尝试找到今天的成长日志页面
            today_title = f"[{date_str}] Maria 成长日志"
            
            client = skill._get_client()
            search_result = client.search(
                query=today_title,
                filter={"property": "object", "value": "page"},
                page_size=3,
            )
            
            existing_page_id = None
            for item in search_result.get("results", []):
                title = skill._extract_title(item)
                if title == today_title:
                    existing_page_id = item["id"]
                    break
            
            if existing_page_id:
                # 追加到已有页面
                blocks = skill._markdown_to_blocks(content)
                client.blocks.children.append(
                    block_id=existing_page_id,
                    children=blocks[:50],
                )
                logger.info(f"[Memory] 成长日志已追加: {len(entries)} 条")
            else:
                # 创建今天的成长日志
                # 获取或创建"成长日志"分区
                growth_section_id = await self._get_growth_section(skill)
                
                header = f"# Maria 成长日志 - {date_str}\n\n"
                header += "记录 Maria 每天学到的新知识、犯的错误、改正的行为。\n\n---\n\n"
                full_content = header + content
                
                blocks = skill._markdown_to_blocks(full_content)
                blocks.append(skill._make_divider())
                blocks.append(skill._make_paragraph(
                    f"由 Maria 学习引擎自动记录",
                    color="gray"
                ))
                
                client.pages.create(
                    parent={"page_id": growth_section_id},
                    properties={
                        "title": [{"text": {"content": today_title}}]
                    },
                    icon={"type": "emoji", "emoji": "🌱"},
                    children=blocks[:100],
                )
                logger.info(f"[Memory] 创建今日成长日志: {today_title}")
        
        except Exception as e:
            logger.warning(f"[Memory] 成长日志写入失败（不影响学习）: {e}")
    
    async def _get_growth_section(self, skill) -> str:
        """获取或创建 Notion 中的"成长日志"分区"""
        section_title = "🌱 成长日志"
        
        try:
            client = skill._get_client()
            root_id = skill._get_root_page_id()
            
            # 搜索是否已有
            search_result = client.search(
                query=section_title,
                filter={"property": "object", "value": "page"},
                page_size=5,
            )
            
            for item in search_result.get("results", []):
                title = skill._extract_title(item)
                if title == section_title:
                    return item["id"]
            
            # 创建
            new_page = client.pages.create(
                parent={"page_id": root_id},
                properties={
                    "title": [{"text": {"content": section_title}}]
                },
                icon={"type": "emoji", "emoji": "🌱"},
                children=[
                    skill._make_paragraph(
                        "Maria 的自我成长日志。每天自动记录学到的新知识、犯的错误和改正的行为。",
                        color="gray"
                    )
                ],
            )
            return new_page["id"]
            
        except Exception as e:
            logger.warning(f"[Memory] 创建成长日志分区失败: {e}")
            return skill._get_root_page_id()


# 单例
memory_service = MemoryService()
