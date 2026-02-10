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
import asyncio

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
    
    # ReAct 最大循环轮次（增加到8轮，处理更复杂的任务）
    MAX_REACT_TURNS = 8
    
    # 记忆系统配置（扩展）
    CONVERSATION_HISTORY_LIMIT = 20  # 对话历史从10增加到20
    RAG_TOP_K = 5  # RAG检索从3增加到5
    
    # 复杂任务关键词（触发高级模型）
    COMPLEX_TASK_KEYWORDS = [
        "分析", "计划", "方案", "策略", "评估", "设计", "架构",
        "合同", "法律", "风险", "财务", "预算", "报告",
        "为什么", "怎么办", "如何", "建议", "优化"
    ]
    
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
        
        # 注入用户偏好记忆 + 行动准则（行动准则权重最高，必须遵守）
        memory_ctx = getattr(self, '_user_memory_context', '')
        if memory_ctx:
            base_prompt += f"\n\n{memory_ctx}"
        
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
            
            # ===== 1.5 邮件上下文检索（新增）=====
            # 当用户提到"那个合同"、"刚才的邮件"等，自动注入相关邮件上下文
            email_context_prompt = None
            try:
                from app.services.email_context_service import email_context_service
                email_context_prompt = await email_context_service.build_context_prompt(user_id, message)
                if email_context_prompt:
                    logger.info(f"[Maria] 检测到邮件引用，已注入上下文")
            except Exception as e:
                logger.warning(f"[Maria] 邮件上下文检索失败: {e}")
            
            # ===== 2. 构建对话消息 =====
            # 如果有邮件上下文，将其作为系统消息注入
            if email_context_prompt:
                augmented_message = f"{email_context_prompt}\n\n---\n**用户请求**: {message}"
            else:
                augmented_message = message
            
            messages = self._build_conversation_messages(augmented_message)
            
            # ===== 3. ReAct 循环 =====
            from app.agents.maria_tools import MARIA_TOOLS, MariaToolExecutor
            from app.core.llm import chat_completion
            
            tool_executor = MariaToolExecutor(self)
            system_prompt = self._build_system_prompt()
            
            final_text = ""
            collected_files = []
            
            for turn in range(self.MAX_REACT_TURNS):
                logger.info(f"[Maria ReAct] 第{turn + 1}轮 | 复杂任务={getattr(self, '_is_complex_task', False)}")
                
                # 智能模型选择：复杂任务用DeepSeek（推理更强），简单任务用Qwen（更便宜）
                model_pref = "reasoning" if getattr(self, '_is_complex_task', False) else None
                
                response = await chat_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=MARIA_TOOLS,
                    use_advanced=True,
                    agent_name="Maria",
                    task_type="react_turn",
                    model_preference=model_pref,  # 根据任务复杂度选择模型
                )
                
                # --- 情况A：纯文本回复（没有工具调用）---
                tool_calls = response.get("tool_calls") if isinstance(response, dict) else None
                
                if not tool_calls:
                    content = response.get("content", "") if isinstance(response, dict) else str(response)
                    
                    # 拦截"口头承诺"
                    strong_promises = ["处理好了", "完成了", "已经添加", "已经生成", "已经发送", "同步完成", "添加成功"]
                    task_verbs = ["同步", "添加", "生成", "发送", "查询", "检查", "分析", "看看", "读取"]
                    valid_responses = ["没有", "不能", "无法", "不支持", "暂时", "清净", "空的", "0封"]
                    
                    has_strong_promise = any(word in content for word in strong_promises)
                    user_requests_task = any(verb in message for verb in task_verbs)
                    is_valid_response = any(word in content for word in valid_responses)
                    
                    # 特殊拦截：用户要分析合同/附件/文件时，必须调用工具
                    attachment_keywords = ["合同", "附件", "文件", "发票", "报价", "提单", "文档"]
                    user_wants_attachment = any(kw in message for kw in attachment_keywords) and "分析" in message
                    response_says_failed = any(word in content for word in ["失败", "无法读取", "正文为空", "方案"])
                    
                    should_intercept = has_strong_promise or (user_requests_task and not is_valid_response and len(content) < 50)
                    
                    # 强制拦截：用户要分析附件但回复说失败，必须重试并调用 analyze_email_attachment
                    if turn == 0 and user_wants_attachment and response_says_failed:
                        logger.warning(f"[Maria ReAct] 拦截：用户要分析附件但回复说失败 | user: '{message[:30]}...'")
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "❌ 错误：你必须调用 analyze_email_attachment 工具去邮箱搜索并分析附件。你有专属邮箱，邮件都在那里，不能说'读取失败'。立即调用工具搜索关键词找到邮件。"})
                        continue
                    
                    if turn == 0 and should_intercept:
                        logger.warning(f"[Maria ReAct] 拦截：口头承诺或任务请求未调工具 | user: '{message[:30]}...' | bot: '{content[:30]}...'")
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "❌ 错误：你必须调用工具执行实际操作，不能只说不做或编造数据。请重新回答，这次必须使用工具。"})
                        continue
                        
                    final_text = content
                    break
                
                # --- 情况B：有工具调用 -> 并行执行工具 + 继续循环 ---
                assistant_msg = {
                    "role": "assistant",
                    "content": response.get("content") or "",
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_msg)
                
                # 准备并行任务
                tool_tasks = []
                tool_call_indices = [] # 保持顺序对应

                for i, tool_call in enumerate(tool_calls):
                    func_name = tool_call["function"]["name"]
                    try:
                        arguments = json.loads(tool_call["function"]["arguments"])
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}
                    
                    # 前端日志脱敏
                    safe_args_str = json.dumps(arguments, ensure_ascii=False)
                    if "password" in safe_args_str.lower():
                        safe_args_str = "******"
                    else:
                        safe_args_str = safe_args_str[:100]

                    await self.log_live_step("action", f"执行: {func_name}", safe_args_str)
                    
                    # 添加到任务列表
                    tool_tasks.append(tool_executor.execute(func_name, arguments, user_id))
                    tool_call_indices.append(i)
                
                # 并行执行所有工具
                if tool_tasks:
                    results = await asyncio.gather(*tool_tasks)
                    
                    # 处理结果
                    for i, tool_result in enumerate(results):
                        original_index = tool_call_indices[i]
                        tool_call = tool_calls[original_index]
                        func_name = tool_call["function"]["name"]

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
            
            # ===== 3.5 自我验证机制 =====
            final_text = await self._self_verify_response(message, final_text, messages)
            
            # ===== 4. 构建返回结果 =====
            result = {"success": True, "response": final_text}
            
            if collected_files:
                result["filepath"] = collected_files[0]
            
            # ===== 5. 保存交互 + 异步学习 =====
            await self._save_interaction(user_id, message, message_type, {"type": "react"}, final_text)
            
            try:
                from app.services.memory_service import memory_service
                asyncio.create_task(memory_service.auto_learn(user_id, message, final_text))
            except Exception:
                pass
            
            # RAG: 异步摄取对话到向量库
            try:
                from app.services.vector_store import vector_store
                asyncio.create_task(vector_store.ingest_conversation(user_id, message, final_text))
            except Exception:
                pass
            
            await self.end_task_session("处理完成")
            return result
            
        except Exception as e:
            logger.error(f"[Maria] 处理消息失败: {e}", exc_info=True)
            await self.log_error(str(e))
            await self.end_task_session(error_message=str(e))
            
            # 生成对老板有用的错误说明
            error_msg = str(e)
            user_friendly = self._build_error_report(error_msg, message)
            
            return {
                "success": False,
                "response": user_friendly,
                "error": error_msg
            }
    
    @staticmethod
    def _build_error_report(error_msg: str, user_request: str) -> str:
        """把技术错误翻译成老板能看懂的汇报"""
        
        # 错误类型识别与翻译
        error_map = [
            # Notion 相关
            ("NOTION_API_KEY", "Notion API 密钥未配置或已失效，需要重新设置"),
            ("NOTION_ROOT_PAGE_ID", "Notion 根页面未配置，需要设置 Maria 工作台的页面 ID"),
            ("notion", "Notion 连接出了问题，可能是权限不足或者网络超时"),
            ("Could not find page", "找不到 Notion 页面，可能页面被删了或者没给我权限"),
            ("Unauthorized", "Notion 授权失败，API 密钥可能过期了"),
            
            # 邮件相关
            ("IMAP", "邮箱连接失败（IMAP协议问题），可能是密码错了或者服务器拒绝了"),
            ("SMTP", "邮件发送失败（SMTP协议问题），可能是授权码过期了"),
            ("email", "邮件操作失败"),
            
            # 数据库相关
            ("database", "数据库连接出了问题"),
            ("relation", "数据库表还没创建"),
            ("asyncpg", "数据库连接超时或断开了"),
            
            # 网络相关
            ("timeout", "操作超时了，网络可能不太好"),
            ("ConnectionError", "网络连接失败"),
            ("httpx", "网络请求失败"),
            
            # LLM 相关
            ("rate_limit", "AI 接口调用太频繁了，被限流了，稍等一下再试"),
            ("insufficient_quota", "AI 接口额度用完了，需要充值"),
            ("model", "AI 模型调用出了问题"),
            
            # 权限相关
            ("Permission", "权限不够，无法执行这个操作"),
            ("Forbidden", "被拒绝了，没有权限"),
            
            # 通用
            ("asyncio", "内部并发处理出了问题"),
            ("JSON", "数据解析出了问题"),
        ]
        
        # 匹配错误类型
        diagnosis = None
        for keyword, desc in error_map:
            if keyword.lower() in error_msg.lower():
                diagnosis = desc
                break
        
        if not diagnosis:
            diagnosis = f"出了一个意外错误"
        
        # 构建清晰的错误汇报
        report = f"老板，你让我「{user_request[:30]}」的时候出了问题。\n\n"
        report += f"原因：{diagnosis}\n"
        report += f"错误详情：{error_msg[:150]}\n\n"
        report += "我已经记录了这个问题。你可以让我再试一次，或者告诉开发团队排查。"
        
        return report
    
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
            self._recent_history = await self._load_recent_history(user_id, limit=self.CONVERSATION_HISTORY_LIMIT)
        except Exception as e:
            logger.warning(f"[Maria] 加载对话历史失败: {e}")
        
        # RAG: 检索相关历史上下文（扩展到5条）
        self._rag_context = ""
        try:
            from app.services.vector_store import vector_store
            self._rag_context = await vector_store.get_relevant_context(user_id, message, top_k=self.RAG_TOP_K)
        except Exception as e:
            logger.debug(f"[Maria] RAG检索跳过: {e}")
        
        # 判断是否为复杂任务（决定是否使用高级模型）
        self._is_complex_task = any(kw in message for kw in self.COMPLEX_TASK_KEYWORDS)
        if self._is_complex_task:
            logger.info(f"[Maria] 检测到复杂任务，将使用高级模型")
    
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
    
    # ==================== 自我验证机制 ====================
    
    async def _self_verify_response(self, user_message: str, response: str, conversation: list) -> str:
        """
        自我验证机制 - 检查回复质量，必要时优化
        
        检查项：
        1. 是否空洞无物（只说"处理好了"但没有具体内容）
        2. 是否遗漏了用户提到的事项
        3. 是否过于冗长或过于简短
        """
        # 空洞回复检测
        empty_responses = [
            "好的，处理好了", "搞定了", "已处理", "好的", "收到",
            "没问题", "已经完成", "处理完成", "OK", "ok"
        ]
        
        response_stripped = response.strip()
        is_empty = any(response_stripped == er for er in empty_responses) or len(response_stripped) < 15
        
        # 任务关键词检测（用户是否要求做某事）
        task_keywords = ["帮我", "看看", "查一下", "分析", "发送", "添加", "创建", "生成", "同步", "检查"]
        user_requested_task = any(kw in user_message for kw in task_keywords)
        
        # 如果用户要求做事但回复太空洞，触发补充
        if user_requested_task and is_empty:
            logger.warning(f"[Maria 自检] 检测到空洞回复，尝试补充: '{response_stripped}'")
            
            # 检查conversation中是否有工具调用结果
            tool_results = []
            for msg in conversation:
                if msg.get("role") == "tool":
                    try:
                        content = msg.get("content", "")
                        if content:
                            result = json.loads(content) if isinstance(content, str) else content
                            tool_results.append(result)
                    except:
                        pass
            
            # 如果有工具结果，用它来补充回复
            if tool_results:
                supplement = self._generate_result_summary(tool_results)
                if supplement:
                    response = f"{response_stripped}\n\n{supplement}"
                    logger.info(f"[Maria 自检] 已补充工具执行结果摘要")
        
        # 多任务遗漏检测
        # 简单检测：如果用户消息中有"和"、"另外"、"还有"等词，检查回复是否覆盖
        multi_task_indicators = ["和", "另外", "还有", "以及", "同时", "顺便"]
        if any(ind in user_message for ind in multi_task_indicators):
            # 这里只是记录日志，更复杂的遗漏检测需要LLM辅助
            logger.debug(f"[Maria 自检] 检测到多任务请求，请确保全部处理")
        
        return response
    
    @staticmethod
    def _generate_result_summary(tool_results: list) -> str:
        """根据工具执行结果生成摘要"""
        summaries = []
        
        for result in tool_results:
            if not isinstance(result, dict):
                continue
            
            status = result.get("status", result.get("success", ""))
            
            # 邮件相关
            if "emails" in result or "email" in str(result.get("message", "")):
                count = result.get("count", result.get("total", 0))
                if count:
                    summaries.append(f"邮件：共{count}封")
            
            # 日程相关
            if "schedule" in result or "calendar" in str(result.get("message", "")):
                if result.get("success") or status == "success":
                    summaries.append("日程：已添加")
            
            # 任务分配相关
            if "task" in result and "agent" in str(result):
                agent = result.get("agent_name", "")
                if agent:
                    summaries.append(f"任务：已分配给{agent}")
            
            # Notion相关
            if "notion" in str(result).lower() or "page_url" in result:
                url = result.get("page_url", result.get("url", ""))
                if url:
                    summaries.append(f"Notion：{url}")
        
        return "执行结果：" + "；".join(summaries) if summaries else ""


# 创建单例并注册（保持向后兼容）
clauwdbot_agent = ClauwdbotAgent()
assistant_agent = clauwdbot_agent  # 向后兼容别名
AgentRegistry.register(clauwdbot_agent)
