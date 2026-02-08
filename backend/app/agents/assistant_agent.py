"""
Clauwdbot - AI中心超级助理（编排层）

Phase 1 重构后，本文件只保留:
1. ReAct 循环 (Think -> Act -> Observe)
2. 上下文管理（对话历史、记忆、审批）
3. 交互记录保存
4. 主动推送（提醒/预览）

所有业务逻辑已迁移到 app.skills.* 模块。
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import json
import os
import pytz

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from sqlalchemy import text
from app.core.prompts.clauwdbot import CLAUWDBOT_SYSTEM_PROMPT, AGENT_MANAGEMENT_PROMPT, AGENT_UPGRADE_PROMPT


class ClauwdbotAgent(BaseAgent):
    """Clauwdbot - AI中心超级助理（编排层）
    
    负责 ReAct 循环和上下文管理，
    具体业务逻辑委托给 app.skills.* 模块。
    """
    
    name = "Clauwdbot"
    agent_type = AgentType.ASSISTANT
    description = "AI中心超级助理 - 最高权限执行官，管理AI团队、个人助理、代码编写"
    
    # 中国时区
    CHINA_TZ = pytz.timezone('Asia/Shanghai')
    
    # ==================== 权限控制 ====================
    
    ALLOWED_READ_PATHS = [
        "backend/app/agents/",
        "backend/app/core/prompts/",
        "backend/app/services/",
        "backend/app/scheduler/",
    ]
    
    ALLOWED_WRITE_PATHS = [
        "backend/app/core/prompts/",
        "backend/app/agents/",
    ]
    
    FORBIDDEN_FILES = [
        "backend/app/agents/base.py",
        "backend/app/models/database.py",
        "backend/app/core/config.py",
        "backend/app/core/llm.py",
    ]
    
    # AI员工信息映射（仍需在此保留，供审批流程使用）
    AGENT_INFO = {
        "coordinator": {"name": "小调", "type": AgentType.COORDINATOR, "prompt_file": "coordinator.py"},
        "video_creator": {"name": "小影", "type": AgentType.VIDEO_CREATOR, "prompt_file": None},
        "copywriter": {"name": "小文", "type": AgentType.COPYWRITER, "prompt_file": None},
        "sales": {"name": "小销", "type": AgentType.SALES, "prompt_file": None},
        "follow": {"name": "小跟", "type": AgentType.FOLLOW, "prompt_file": None},
        "analyst": {"name": "小析", "type": AgentType.ANALYST, "prompt_file": None},
        "lead_hunter": {"name": "小猎", "type": AgentType.LEAD_HUNTER, "prompt_file": "lead_hunter.py"},
        "analyst2": {"name": "小析2", "type": AgentType.ANALYST2, "prompt_file": "analyst2.py"},
        "eu_customs_monitor": {"name": "小欧间谍", "type": AgentType.EU_CUSTOMS_MONITOR, "prompt_file": "eu_customs_monitor.py"},
    }
    
    # ReAct 最大循环轮次
    MAX_REACT_TURNS = 5
    
    @staticmethod
    def to_china_time(dt):
        """转换为中国时区时间"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(ClauwdbotAgent.CHINA_TZ)
    
    def _build_system_prompt(self) -> str:
        bot_name = getattr(self, '_bot_display_name', None) or "Clauwdbot"
        base_prompt = CLAUWDBOT_SYSTEM_PROMPT.format(bot_name=bot_name)
        
        # 注入用户偏好记忆
        memory_ctx = getattr(self, '_user_memory_context', '')
        if memory_ctx:
            base_prompt += f"\n\n关于老板的偏好（请据此调整回复）：\n{memory_ctx}"
        
        # 注入RAG检索到的相关历史（Phase 2）
        rag_ctx = getattr(self, '_rag_context', '')
        if rag_ctx:
            base_prompt += f"\n\n{rag_ctx}"
        
        return base_prompt
    
    # ==================== 核心：ReAct 循环 ====================
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户消息 - Maria/Clauwdbot 大模型原生对话引擎
        
        架构：ReAct (Reasoning + Acting) 循环
        LLM 自主决定是直接回复还是调用工具干活，最多循环 MAX_REACT_TURNS 轮
        """
        message = input_data.get("message", "")
        user_id = input_data.get("user_id", "")
        message_type = input_data.get("message_type", "text")
        file_url = input_data.get("file_url")
        
        await self.start_task_session("process_message", f"处理消息: {message[:50]}...")
        
        try:
            # ===== 0. 前置准备（记忆、纠错、审批检测）=====
            await self._pre_process(user_id, message)
            
            # 审批检测
            try:
                from app.services.memory_service import memory_service
                pending_raw = await memory_service.recall(user_id, "pending_approval")
                if pending_raw:
                    approval_result = await self._check_approval(user_id, message, pending_raw)
                    if approval_result:
                        await self._save_interaction(user_id, message, message_type, {"type": "approval"}, approval_result.get("response", ""))
                        await self.end_task_session("审批处理完成")
                        return approval_result
            except Exception as e:
                logger.warning(f"[Maria] 审批检测失败: {e}")
            
            # ===== 1. 音频/文件直接处理 =====
            if message_type in ["voice", "file"] and file_url:
                result = await self._handle_audio_file(file_url, user_id)
                await self.end_task_session("音频处理完成")
                return result
            
            # ===== 2. 构建对话消息 =====
            messages = self._build_conversation_messages(message)
            
            # ===== 3. ReAct 循环 =====
            from app.agents.maria_tools import MARIA_TOOLS, MariaToolExecutor
            from app.core.llm import chat_completion
            
            tool_executor = MariaToolExecutor(self)
            system_prompt = self._build_system_prompt()
            
            final_text = ""
            collected_files = []
            
            for turn in range(self.MAX_REACT_TURNS):
                logger.info(f"[Maria ReAct] 第{turn + 1}轮")
                
                response = await chat_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=MARIA_TOOLS,
                    use_advanced=True,
                    agent_name="Maria",
                    task_type="react_turn",
                )
                
                # --- 情况A：纯文本回复（没有工具调用）---
                tool_calls = response.get("tool_calls") if isinstance(response, dict) else None
                
                if not tool_calls:
                    content = response.get("content", "") if isinstance(response, dict) else str(response)
                    
                    # 拦截"口头承诺"
                    strong_promises = ["处理好了", "完成了", "已经添加", "已经生成", "已经发送", "同步完成", "添加成功"]
                    task_verbs = ["同步", "添加", "生成", "发送", "查询", "检查"]
                    valid_responses = ["没有", "不能", "无法", "不支持", "暂时", "清净", "空的", "0封", "问题", "失败"]
                    
                    has_strong_promise = any(word in content for word in strong_promises)
                    user_requests_task = any(verb in message for verb in task_verbs)
                    is_valid_response = any(word in content for word in valid_responses)
                    
                    should_intercept = has_strong_promise or (user_requests_task and not is_valid_response and len(content) < 50)
                    
                    if turn == 0 and should_intercept:
                        logger.warning(f"[Maria ReAct] 拦截：口头承诺或任务请求未调工具 | user: '{message[:30]}...' | bot: '{content[:30]}...'")
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "❌ 错误：你必须调用工具执行实际操作，不能只说不做或编造数据。请重新回答，这次必须使用工具。"})
                        continue
                        
                    final_text = content
                    break
                
                # --- 情况B：有工具调用 -> 执行工具 + 继续循环 ---
                assistant_msg = {
                    "role": "assistant",
                    "content": response.get("content") or "",
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_msg)
                
                for tool_call in tool_calls:
                    func_name = tool_call["function"]["name"]
                    try:
                        arguments = json.loads(tool_call["function"]["arguments"])
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}
                    
                    await self.log_live_step("action", f"执行: {func_name}", json.dumps(arguments, ensure_ascii=False)[:100])
                    
                    tool_result = await tool_executor.execute(func_name, arguments, user_id)
                    
                    if tool_result.get("filepath"):
                        collected_files.append(tool_result["filepath"])
                    
                    tool_result_str = json.dumps(tool_result, ensure_ascii=False, default=str)
                    if len(tool_result_str) > 3000:
                        tool_result_str = tool_result_str[:3000] + "...(结果已截断)"
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result_str,
                    })
                    
                    logger.info(f"[Maria ReAct] 工具 {func_name} 执行完毕")
            else:
                if not final_text:
                    final_text = "好的，处理好了。"
            
            # ===== 4. 构建返回结果 =====
            result = {"success": True, "response": final_text}
            
            if collected_files:
                result["filepath"] = collected_files[0]
            
            # ===== 5. 保存交互 + 异步学习 =====
            await self._save_interaction(user_id, message, message_type, {"type": "react"}, final_text)
            
            try:
                from app.services.memory_service import memory_service
                import asyncio
                asyncio.create_task(memory_service.auto_learn(user_id, message, final_text))
            except Exception:
                pass
            
            # RAG: 异步摄取对话到向量库
            try:
                from app.services.vector_store import vector_store
                import asyncio
                asyncio.create_task(vector_store.ingest_conversation(user_id, message, final_text))
            except Exception:
                pass
            
            await self.end_task_session("处理完成")
            return result
            
        except Exception as e:
            logger.error(f"[Maria] 处理消息失败: {e}")
            await self.log_error(str(e))
            await self.end_task_session(error_message=str(e))
            return {
                "success": False,
                "response": "老板，出了点小状况，我再试试。",
                "error": str(e)
            }
    
    # ==================== 前置处理 ====================
    
    async def _pre_process(self, user_id: str, message: str):
        """前置处理：加载记忆、纠错检测"""
        try:
            from app.services.memory_service import memory_service
            memory_context = await memory_service.get_context_for_llm(user_id)
            if memory_context:
                self._user_memory_context = memory_context
            
            bot_name = await memory_service.recall(user_id, "bot_name")
            if bot_name:
                self._bot_display_name = bot_name
            else:
                self._bot_display_name = "Clauwdbot"
        except Exception as e:
            logger.warning(f"[Maria] 加载记忆失败: {e}")
        
        try:
            from app.services.memory_service import memory_service
            if await memory_service.detect_correction(message):
                await memory_service.learn_from_correction(user_id, "", message)
        except Exception as e:
            logger.warning(f"[Maria] 纠错检测失败: {e}")
        
        self._recent_history = []
        try:
            self._recent_history = await self._load_recent_history(user_id, limit=10)
        except Exception as e:
            logger.warning(f"[Maria] 加载对话历史失败: {e}")
        
        # RAG: 检索相关历史上下文
        self._rag_context = ""
        try:
            from app.services.vector_store import vector_store
            self._rag_context = await vector_store.get_relevant_context(user_id, message, top_k=3)
        except Exception as e:
            logger.debug(f"[Maria] RAG检索跳过: {e}")
    
    def _build_conversation_messages(self, current_message: str) -> List[Dict[str, str]]:
        """构建发送给 LLM 的对话消息列表（含历史上下文）"""
        messages = []
        
        for hist in getattr(self, '_recent_history', []):
            role = hist.get("role", "user")
            content = hist.get("content", "")
            if content:
                messages.append({"role": role, "content": content[:500]})
        
        messages.append({"role": "user", "content": current_message})
        return messages
    
    # ==================== 审批流程 ====================
    
    APPROVAL_KEYWORDS = ["同意", "通过", "可以", "行", "好的", "执行", "改吧", "去做吧", "没问题", "ok", "OK", "确认"]
    REJECT_KEYWORDS = ["不行", "取消", "算了", "不要", "不改", "先不", "等等", "暂时不"]
    
    async def _check_approval(self, user_id: str, message: str, pending_raw: str) -> Optional[Dict[str, Any]]:
        """检查用户消息是否是对待审批方案的回复"""
        message_stripped = message.strip()
        
        is_approve = any(kw in message_stripped for kw in self.APPROVAL_KEYWORDS)
        is_reject = any(kw in message_stripped for kw in self.REJECT_KEYWORDS)
        
        if not is_approve and not is_reject:
            if len(message_stripped) > 10:
                return None
            return None
        
        try:
            pending_data = json.loads(pending_raw)
        except (json.JSONDecodeError, TypeError):
            from app.services.memory_service import memory_service
            await memory_service.forget(user_id, "pending_approval")
            return None
        
        from app.services.memory_service import memory_service
        
        if is_reject:
            await memory_service.forget(user_id, "pending_approval")
            return {"success": True, "response": "好的，那先不改了。"}
        
        if is_approve:
            result = await self._execute_approved_plan(user_id, pending_data)
            await memory_service.forget(user_id, "pending_approval")
            return result
        
        return None
    
    async def _execute_approved_plan(self, user_id: str, plan_data: Dict) -> Dict[str, Any]:
        """执行已审批的方案"""
        plan_type = plan_data.get("type", "")
        
        if plan_type in ("agent_code_modify", "agent_upgrade"):
            target_agent_key = plan_data.get("target_agent")
            new_prompt = plan_data.get("new_prompt", "")
            agent_name = plan_data.get("agent_name", target_agent_key)
            
            if not target_agent_key or not new_prompt:
                return {"success": False, "response": "方案数据不完整，没法执行。你再说一遍要改什么？"}
            
            try:
                agent_info = self.AGENT_INFO.get(target_agent_key)
                if agent_info:
                    agent = AgentRegistry.get(agent_info["type"])
                    if agent:
                        agent.system_prompt = new_prompt
                        logger.info(f"[Clauwdbot] 审批通过，已修改{agent_name}的Prompt")
                        
                        prompt_file = agent_info.get("prompt_file")
                        if prompt_file:
                            filepath = f"backend/app/core/prompts/{prompt_file}"
                            await self.write_agent_file(
                                filepath,
                                f'"""\n{agent_name} 的系统Prompt\n"""\n\nSYSTEM_PROMPT = """{new_prompt}"""\n'
                            )
                        
                        return {"success": True, "response": f"搞定了，{agent_name}的Prompt已经改好并生效了。"}
                
                return {"success": False, "response": f"找不到{agent_name}，改不了。"}
                
            except Exception as e:
                logger.error(f"[Clauwdbot] 执行审批方案失败: {e}")
                return {"success": False, "response": f"执行的时候出了点问题：{str(e)[:100]}"}
        
        else:
            return {"success": False, "response": "这个方案我不知道怎么执行，你直接告诉我要做什么吧。"}
    
    # ==================== 文件操作能力（受限） ====================
    
    def _is_path_allowed(self, filepath: str, for_write: bool = False) -> bool:
        """检查文件路径是否在允许范围内"""
        for forbidden in self.FORBIDDEN_FILES:
            if forbidden in filepath:
                return False
        
        allowed_paths = self.ALLOWED_WRITE_PATHS if for_write else self.ALLOWED_READ_PATHS
        for allowed in allowed_paths:
            if allowed in filepath:
                return True
        
        return False
    
    async def read_agent_file(self, filepath: str) -> Dict[str, Any]:
        """读取AI员工相关文件（受限）"""
        if not self._is_path_allowed(filepath, for_write=False):
            return {"success": False, "error": f"权限不足：无法读取 {filepath}。此文件属于系统底层架构。"}
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            full_path = os.path.join(base_dir, filepath.replace("backend/", ""))
            
            if not os.path.exists(full_path):
                return {"success": False, "error": f"文件不存在: {filepath}"}
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {"success": True, "content": content, "filepath": filepath}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def write_agent_file(self, filepath: str, content: str) -> Dict[str, Any]:
        """写入/修改AI员工相关文件（受限，只能改绿区）"""
        if not self._is_path_allowed(filepath, for_write=True):
            return {"success": False, "error": f"权限不足：无法修改 {filepath}。这个文件属于系统底层。"}
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            full_path = os.path.join(base_dir, filepath.replace("backend/", ""))
            
            if os.path.exists(full_path):
                backup_path = full_path + ".bak"
                import shutil
                shutil.copy2(full_path, backup_path)
                logger.info(f"[Clauwdbot] 已备份: {filepath} -> {filepath}.bak")
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"[Clauwdbot] 文件已修改: {filepath}")
            return {"success": True, "filepath": filepath}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== 音频处理 ====================
    
    async def _handle_audio_file(self, file_url: str, user_id: str) -> Dict[str, Any]:
        """处理音频文件（会议录音）"""
        await self.log_live_step("fetch", "下载音频文件", file_url[:50])
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    INSERT INTO meeting_records (audio_file_url, transcription_status)
                    VALUES (:url, 'processing')
                    RETURNING id
                """),
                {"url": file_url}
            )
            meeting_id = result.fetchone()[0]
            await db.commit()
        
        return {
            "success": True,
            "response": "已收到会议录音！正在处理中，转写完成后会自动发送会议纪要给你。预计需要2-5分钟",
            "meeting_id": str(meeting_id),
            "async_task": "speech_transcription"
        }
    
    # ==================== 工具方法 ====================
    
    async def _load_recent_history(self, user_id: str, limit: int = 6) -> List[Dict]:
        """加载最近的对话历史"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT content, response, interaction_type, created_at
                        FROM assistant_interactions
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "limit": limit}
                )
                rows = result.fetchall()
            
            if not rows:
                return []
            
            history = []
            for row in reversed(rows):
                content, response, intent_type, _ = row[0], row[1], row[2], row[3]
                if content:
                    history.append({"role": "user", "content": content})
                if response:
                    history.append({"role": "assistant", "content": response})
            
            return history
            
        except Exception as e:
            logger.warning(f"[Clauwdbot] 加载对话历史失败: {e}")
            return []
    
    async def _save_interaction(self, user_id: str, message: str, message_type: str,
                                intent: Dict, response: str):
        """保存交互记录"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO assistant_interactions 
                        (user_id, message_type, content, interaction_type, intent_parsed, response, response_sent)
                        VALUES (:user_id, :message_type, :content, :interaction_type, :intent_parsed, :response, TRUE)
                    """),
                    {
                        "user_id": user_id,
                        "message_type": message_type,
                        "content": message,
                        "interaction_type": intent.get("type", "unknown"),
                        "intent_parsed": json.dumps(intent, ensure_ascii=False),
                        "response": response
                    }
                )
                await db.commit()
        except Exception as e:
            logger.error(f"[Clauwdbot] 保存交互记录失败: {e}")
    
    # ==================== 主动推送方法 ====================
    
    async def send_tomorrow_preview(self, user_id: str) -> Optional[str]:
        """发送明日安排预览"""
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT title, start_time, location, priority
                    FROM assistant_schedules
                    WHERE DATE(start_time) = :tomorrow
                    AND is_completed = FALSE
                    AND reminder_sent_day_before = FALSE
                    ORDER BY start_time ASC
                """),
                {"tomorrow": tomorrow}
            )
            schedules = result.fetchall()
            
            if not schedules:
                return None
            
            await db.execute(
                text("""
                    UPDATE assistant_schedules SET reminder_sent_day_before = TRUE
                    WHERE DATE(start_time) = :tomorrow
                """),
                {"tomorrow": tomorrow}
            )
            await db.commit()
        
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][tomorrow.weekday()]
        lines = [f"明日安排预览（{tomorrow.month}月{tomorrow.day}日 {weekday}）"]
        
        for s in schedules:
            china_time = self.to_china_time(s[1])
            time_str = china_time.strftime("%H:%M")
            location_str = f" - {s[2]}" if s[2] else ""
            priority_icon = {"urgent": "🔴", "high": "🟡"}.get(s[3], "")
            lines.append(f"{time_str} {priority_icon}{s[0]}{location_str}")
        
        lines.append(f"\n共{len(schedules)}项安排，请做好准备！")
        return "\n".join(lines)
    
    async def get_due_reminders(self) -> List[Dict[str, Any]]:
        """获取需要发送的提醒"""
        now = datetime.now()
        reminders = []
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT id, title, start_time, location, reminder_minutes
                    FROM assistant_schedules
                    WHERE is_completed = FALSE
                    AND reminder_sent = FALSE
                    AND reminder_minutes > 0
                    AND start_time BETWEEN NOW() AND NOW() + (reminder_minutes || ' minutes')::INTERVAL
                """)
            )
            
            for row in result.fetchall():
                reminders.append({
                    "schedule_id": str(row[0]),
                    "title": row[1],
                    "start_time": row[2],
                    "location": row[3],
                    "minutes_before": row[4]
                })
                
                await db.execute(
                    text("UPDATE assistant_schedules SET reminder_sent = TRUE WHERE id = :id"),
                    {"id": row[0]}
                )
            
            await db.commit()
        
        return reminders


# 创建单例并注册（保持向后兼容）
clauwdbot_agent = ClauwdbotAgent()
assistant_agent = clauwdbot_agent  # 向后兼容别名
AgentRegistry.register(clauwdbot_agent)
