"""
Clauwdbot - AI中心超级助理（由小助升级而来）
最高权限执行官，仅次于老板

核心能力：
1. 个人助理 - 日程管理、会议纪要、待办事项、邮件管理、ERP数据
2. AI团队管理 - 查看状态、分配任务、协调工作流
3. AI员工升级 - 读取/修改AI员工Prompt和业务代码
4. 系统监控 - 系统健康、API可用性、AI用量
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import json
import re
import os
import pytz

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from sqlalchemy import text
from app.core.prompts.clauwdbot import CLAUWDBOT_SYSTEM_PROMPT, AGENT_MANAGEMENT_PROMPT, AGENT_UPGRADE_PROMPT


class ClauwdbotAgent(BaseAgent):
    """Clauwdbot - AI中心超级助理
    
    最高权限执行官，仅次于老板。
    
    核心能力：
    1. 个人助理 - 日程管理、会议纪要、待办事项、邮件管理、ERP数据
    2. AI团队管理 - 查看状态、分配任务、协调工作流
    3. AI员工升级 - 读取/修改AI员工Prompt和业务代码
    4. 系统监控 - 系统健康、API可用性、AI用量
    """
    
    name = "Clauwdbot"
    agent_type = AgentType.ASSISTANT
    description = "AI中心超级助理 - 最高权限执行官，管理AI团队、个人助理、代码编写"
    
    # 中国时区
    CHINA_TZ = pytz.timezone('Asia/Shanghai')
    
    # ==================== 权限控制 ====================
    
    # 允许读取的文件路径（绿区）
    ALLOWED_READ_PATHS = [
        "backend/app/agents/",
        "backend/app/core/prompts/",
        "backend/app/services/",
        "backend/app/scheduler/",
    ]
    
    # 允许写入的文件路径（绿区）
    ALLOWED_WRITE_PATHS = [
        "backend/app/core/prompts/",  # 可修改AI员工Prompt
        "backend/app/agents/",         # 可修改AI员工代码
    ]
    
    # 禁止修改的文件（红区）
    FORBIDDEN_FILES = [
        "backend/app/agents/base.py",
        "backend/app/models/database.py",
        "backend/app/core/config.py",
        "backend/app/core/llm.py",
    ]
    
    # AI员工信息映射
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
        
        # 如果有记忆上下文，动态注入
        memory_ctx = getattr(self, '_user_memory_context', '')
        if memory_ctx:
            base_prompt += f"\n\n关于老板的偏好（请据此调整回复）：\n{memory_ctx}"
        
        return base_prompt
    
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
            
            # 审批检测：如果有待审批方案且用户在回复审批
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
            collected_files = []  # 收集工具返回的文件
            
            for turn in range(self.MAX_REACT_TURNS):
                logger.info(f"[Maria ReAct] 第{turn + 1}轮")
                
                response = await chat_completion(
                    messages=messages,
                    system_prompt=system_prompt,
                    tools=MARIA_TOOLS,
                    use_advanced=True,  # 优先用 DeepSeek
                    agent_name="Maria",
                    task_type="react_turn",
                )
                
                # --- 情况A：纯文本回复（没有工具调用）---
                tool_calls = response.get("tool_calls") if isinstance(response, dict) else None
                
                if not tool_calls:
                    content = response.get("content", "") if isinstance(response, dict) else str(response)
                    
                    # 拦截“口头承诺”：如果回复里说要操作但没调工具，强制它再想一次
                    commitment_keywords = ["稍等", "操作一下", "正在处理", "为您添加", "为您生成", "为您查询"]
                    if any(kw in content for kw in commitment_keywords) and turn == 0:
                        logger.warning(f"[Maria ReAct] 拦截到口头承诺但未行动，强制重试: {content[:50]}...")
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": "请立刻调用工具执行你刚才说的操作，不要只说不做。"})
                        continue
                        
                    final_text = content
                    break
                
                # --- 情况B：有工具调用 -> 执行工具 + 继续循环 ---
                # 先把 assistant 的 tool_calls 消息加入对话
                assistant_msg = {
                    "role": "assistant",
                    "content": response.get("content") or "",
                    "tool_calls": tool_calls,
                }
                messages.append(assistant_msg)
                
                # 执行每个工具调用
                for tool_call in tool_calls:
                    func_name = tool_call["function"]["name"]
                    try:
                        arguments = json.loads(tool_call["function"]["arguments"])
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}
                    
                    await self.log_live_step("action", f"执行: {func_name}", json.dumps(arguments, ensure_ascii=False)[:100])
                    
                    # 调用工具
                    tool_result = await tool_executor.execute(func_name, arguments, user_id)
                    
                    # 收集文件路径
                    if tool_result.get("filepath"):
                        collected_files.append(tool_result["filepath"])
                    
                    # 把工具结果加入对话，让 LLM 在下一轮看到
                    tool_result_str = json.dumps(tool_result, ensure_ascii=False, default=str)
                    # 截断过长的工具结果
                    if len(tool_result_str) > 3000:
                        tool_result_str = tool_result_str[:3000] + "...(结果已截断)"
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result_str,
                    })
                    
                    logger.info(f"[Maria ReAct] 工具 {func_name} 执行完毕")
            else:
                # 循环耗尽，取最后一轮的文本
                if not final_text:
                    final_text = "好的，处理好了。"
            
            # ===== 4. 构建返回结果 =====
            result = {"success": True, "response": final_text}
            
            # 如果有文件，附上第一个文件路径（微信一次只发一个文件）
            if collected_files:
                result["filepath"] = collected_files[0]
            
            # ===== 5. 保存交互 + 异步学习 =====
            await self._save_interaction(user_id, message, message_type, {"type": "react"}, final_text)
            
            try:
                import asyncio
                from app.services.memory_service import memory_service
                asyncio.create_task(
                    memory_service.auto_learn(user_id, message, final_text, "react")
                )
            except Exception as e:
                logger.warning(f"[Maria] 异步学习启动失败: {e}")
            
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
    
    async def _pre_process(self, user_id: str, message: str):
        """前置处理：加载记忆、纠错检测"""
        # 加载用户记忆
        try:
            from app.services.memory_service import memory_service
            memory_context = await memory_service.get_context_for_llm(user_id)
            if memory_context:
                self._user_memory_context = memory_context
            
            # 加载自定义名字
            bot_name = await memory_service.recall(user_id, "bot_name")
            if bot_name:
                self._bot_display_name = bot_name
            else:
                self._bot_display_name = "Clauwdbot"
        except Exception as e:
            logger.warning(f"[Maria] 加载记忆失败: {e}")
        
        # 纠错检测
        try:
            from app.services.memory_service import memory_service
            if await memory_service.detect_correction(message):
                await memory_service.learn_from_correction(user_id, "", message)
        except Exception as e:
            logger.warning(f"[Maria] 纠错检测失败: {e}")
        
        # 加载对话历史
        self._recent_history = []
        try:
            self._recent_history = await self._load_recent_history(user_id, limit=10)
        except Exception as e:
            logger.warning(f"[Maria] 加载对话历史失败: {e}")
    
    def _build_conversation_messages(self, current_message: str) -> List[Dict[str, str]]:
        """构建发送给 LLM 的对话消息列表（含历史上下文）"""
        messages = []
        
        # 加入最近对话历史（格式：{"role": "user"/"assistant", "content": "..."}）
        for hist in getattr(self, '_recent_history', []):
            role = hist.get("role", "")
            content = hist.get("content", "")
            if role and content:
                messages.append({"role": role, "content": content})
        
        # 当前消息
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    # ==================== AI团队管理能力 ====================
    
    async def _handle_agent_status(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """查看AI团队工作状态"""
        await self.log_live_step("search", "查询AI团队状态", "获取所有AI员工今日工作数据")
        
        try:
            async with AsyncSessionLocal() as db:
                # 查询各AI员工今日任务统计
                result = await db.execute(
                    text("""
                        SELECT 
                            agent_type,
                            COUNT(*) as total_tasks,
                            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                            COUNT(CASE WHEN status IN ('pending', 'processing') THEN 1 END) as in_progress,
                            MAX(created_at) as last_active
                        FROM ai_tasks
                        WHERE created_at >= CURRENT_DATE
                        GROUP BY agent_type
                        ORDER BY total_tasks DESC
                    """)
                )
                stats = result.fetchall()
                
                # 查询AI员工的注册状态
                agent_result = await db.execute(
                    text("""
                        SELECT agent_type, name, status, tasks_completed_today, 
                               total_tasks_completed, last_active_at
                        FROM ai_agents
                        ORDER BY agent_type
                    """)
                )
                agents = agent_result.fetchall()
            
            # 构造原始数据描述，交给 LLM 口语化回复
            agent_names = {v["type"].value: v["name"] for v in self.AGENT_INFO.values()}
            
            raw_lines = []
            online_count = 0
            offline_count = 0
            
            if agents:
                for agent in agents:
                    is_online = agent[2] in ["active", "online"]
                    if is_online:
                        online_count += 1
                    else:
                        offline_count += 1
                    status_text = "在线" if is_online else "离线"
                    raw_lines.append(f"{agent[1]}：{status_text}，今日{agent[3]}个任务，累计{agent[4]}个任务")
            
            task_lines = []
            if stats:
                for row in stats:
                    name = agent_names.get(row[0], row[0])
                    total = row[1]
                    completed = row[2]
                    failed = row[3]
                    in_progress = row[4]
                    success_rate = (completed / total * 100) if total > 0 else 0
                    task_lines.append(f"{name}：{completed}/{total}完成（成功率{success_rate:.0f}%），进行中{in_progress}，失败{failed}")
            
            context = f"""用户问：{message}
当前时间：{datetime.now(self.CHINA_TZ).strftime('%Y-%m-%d %H:%M')}

团队概况：共{len(agents) if agents else 0}个AI员工，{online_count}个在线，{offline_count}个离线。

各员工状态：
{chr(10).join(raw_lines) if raw_lines else '暂无员工数据'}

今日任务统计：
{chr(10).join(task_lines) if task_lines else '今天暂时没有任务记录'}"""

            smart_response = await self.chat(
                context,
                "你是郑总的私人助理，在微信上聊天。用口语，短句，挑重点说团队情况就好，不要逐个列举。不要用markdown、标签、分隔线。"
            )
            
            return {"success": True, "response": smart_response}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 查询团队状态失败: {e}")
            return {"success": False, "response": f"查询团队状态时出错：{str(e)}"}
    
    async def _handle_agent_dispatch(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """向指定AI员工分配任务"""
        await self.log_live_step("think", "分析任务分配", "识别目标AI员工和任务内容")
        
        # 使用AI分析指令
        dispatch_prompt = f"""分析以下指令，提取任务分配信息：

用户指令：{message}

可用的AI员工（使用agent_type）：
- coordinator (小调) - 调度/报告
- video_creator (小影) - 视频创作
- copywriter (小文) - 文案策划
- sales (小销) - 销售客服
- follow (小跟) - 客户跟进
- analyst (小析) - 数据分析
- lead_hunter (小猎) - 线索搜索
- eu_customs_monitor (小欧间谍) - 海关监控

返回JSON：
{{"target_agent": "agent_type", "task_description": "具体任务内容", "priority": "medium"}}
只返回JSON。
"""
        
        try:
            response = await self.think([{"role": "user", "content": dispatch_prompt}], temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if not json_match:
                return {"success": False, "response": "请明确告诉我要让哪个AI员工做什么任务。"}
            
            dispatch_data = json.loads(json_match.group())
            target_agent_key = dispatch_data.get("target_agent", "")
            task_desc = dispatch_data.get("task_description", message)
            priority = dispatch_data.get("priority", "medium")
            
            # 获取目标Agent信息
            agent_info = self.AGENT_INFO.get(target_agent_key)
            if not agent_info:
                return {"success": False, "response": f"未找到AI员工: {target_agent_key}，请确认员工名称。"}
            
            agent_name = agent_info["name"]
            agent_type = agent_info["type"]
            
            # 获取Agent实例
            target_agent = AgentRegistry.get(agent_type)
            if not target_agent:
                return {"success": False, "response": f"{agent_name}当前未上线，无法分配任务。"}
            
            await self.log_live_step("think", f"分配任务给{agent_name}", task_desc[:100])
            
            # 记录任务到数据库
            import uuid
            task_id = str(uuid.uuid4())
            
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO ai_tasks (id, task_type, agent_type, status, priority, input_data, created_at)
                        VALUES (:id, :task_type, :agent_type, 'pending', :priority, :input_data, NOW())
                    """),
                    {
                        "id": task_id,
                        "task_type": "clauwdbot_dispatch",
                        "agent_type": target_agent_key,
                        "priority": 5,
                        "input_data": json.dumps({
                            "description": task_desc,
                            "from_user": user_id,
                            "source": "clauwdbot",
                            "priority": priority
                        })
                    }
                )
                await db.commit()
            
            task_id_short = task_id[:8]
            
            return {
                "success": True,
                "response": f"✅ 任务已分配\n\n👤 执行者: {agent_name}\n📋 任务: {task_desc[:80]}\n🔖 任务ID: {task_id_short}\n\n⏳ {agent_name}正在执行中...",
                "task_id": task_id,
                "target_agent": target_agent_key,
                "async_execute": True  # 标记需要异步执行
            }
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 任务分配失败: {e}")
            return {"success": False, "response": f"任务分配时出错：{str(e)}"}
    
    async def _handle_agent_upgrade(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """升级AI员工能力（修改Prompt）"""
        await self.log_live_step("think", "分析升级需求", "识别目标AI员工和优化方向")
        
        # 识别目标AI员工
        target_agent_key = None
        target_agent_name = None
        
        for key, info in self.AGENT_INFO.items():
            if info["name"] in message:
                target_agent_key = key
                target_agent_name = info["name"]
                break
        
        if not target_agent_key:
            # 用AI来识别
            identify_prompt = f"""从以下消息中识别要升级的AI员工名称：
消息：{message}

可选AI员工：小调、小影、小文、小销、小跟、小析、小猎、小欧间谍
返回JSON：{{"agent_name": "名称", "agent_key": "英文key"}}
只返回JSON。"""
            
            try:
                resp = await self.think([{"role": "user", "content": identify_prompt}], temperature=0.3)
                match = re.search(r'\{.*\}', resp, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    target_agent_key = data.get("agent_key")
                    target_agent_name = data.get("agent_name")
            except Exception:
                pass
        
        if not target_agent_key or target_agent_key not in self.AGENT_INFO:
            return {
                "success": False,
                "response": "请告诉我要升级哪个AI员工？\n\n可选：小调、小影、小文、小销、小跟、小析、小猎、小欧间谍"
            }
        
        # 读取目标Agent的当前Prompt
        agent = AgentRegistry.get(self.AGENT_INFO[target_agent_key]["type"])
        if not agent:
            return {"success": False, "response": f"{target_agent_name}当前未上线。"}
        
        current_prompt = agent.system_prompt
        
        # 使用AI生成优化建议
        upgrade_prompt = AGENT_UPGRADE_PROMPT.format(
            agent_name=target_agent_name,
            agent_type=target_agent_key,
            current_prompt=current_prompt[:1000],  # 截取前1000字避免太长
            requirement=message
        )
        
        await self.log_live_step("think", f"正在分析{target_agent_name}的优化方案", "生成Prompt优化建议")
        
        try:
            # 生成完整的新 Prompt
            from app.core.llm import chat_completion
            
            full_prompt = f"""你是一个AI工程师助手。老板要求升级AI员工「{target_agent_name}」。

老板的要求：{message}

当前Prompt内容（截取前2000字）：
{current_prompt[:2000]}

请根据老板的要求，生成修改后的完整Prompt。保留核心职责，按要求优化。
只返回修改后的完整Prompt内容。"""
            
            new_prompt = await chat_completion(
                messages=[{"role": "user", "content": full_prompt}],
                use_advanced=True,
                max_tokens=4000,
                temperature=0.5
            )
            
            # 生成变更摘要
            suggestion = await self.think([{"role": "user", "content": upgrade_prompt}], temperature=0.7)
            if len(suggestion) > 800:
                suggestion = suggestion[:800] + "..."
            
            # 存入待审批
            from app.services.memory_service import memory_service
            approval_data = {
                "type": "agent_upgrade",
                "target_agent": target_agent_key,
                "agent_name": target_agent_name,
                "new_prompt": new_prompt,
                "summary": suggestion,
                "created_at": datetime.now().isoformat()
            }
            await memory_service.remember(
                user_id, "pending_approval",
                json.dumps(approval_data, ensure_ascii=False),
                "workflow"
            )
            
            return {
                "success": True,
                "response": f"我看了一下{target_agent_name}的现状，给你出个升级方案：\n\n{suggestion}\n\n你看行不行？说「通过」我就改。"
            }
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 生成升级方案失败: {e}")
            return {"success": False, "response": f"方案生成的时候出了点问题：{str(e)[:100]}"}
    
    async def _handle_agent_code_read(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """查看AI员工代码逻辑"""
        await self.log_live_step("search", "查找AI员工代码", "准备读取代码文件")
        
        # 识别目标AI员工
        target_agent_key = None
        target_agent_name = None
        
        for key, info in self.AGENT_INFO.items():
            if info["name"] in message:
                target_agent_key = key
                target_agent_name = info["name"]
                break
        
        if not target_agent_key:
            return {
                "success": False,
                "response": "请告诉我要查看哪个AI员工的代码？\n\n可选：小调、小影、小文、小销、小跟、小析、小猎、小欧间谍"
            }
        
        # 获取Agent的Prompt信息
        agent = AgentRegistry.get(self.AGENT_INFO[target_agent_key]["type"])
        if not agent:
            return {"success": False, "response": f"{target_agent_name}当前未上线。"}
        
        # 读取Prompt（不暴露完整代码，只展示关键信息）
        prompt_preview = agent.system_prompt[:800] if agent.system_prompt else "无Prompt"
        
        response_text = f"""🤖 {target_agent_name}代码概览

📝 系统提示词预览：
{prompt_preview}

{'...(Prompt较长已截取)' if len(agent.system_prompt or '') > 800 else ''}

📊 基本信息：
• 类型: {target_agent_key}
• 物流专家模式: {'✅开启' if agent.enable_logistics_expertise else '❌关闭'}
• 实时直播: {'✅开启' if agent.enable_live_broadcast else '❌关闭'}"""
        
        return {"success": True, "response": response_text}
    
    async def _handle_system_status(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """检查系统健康状态"""
        await self.log_live_step("search", "检查系统状态", "全面健康检查中")
        
        try:
            # 调用小调的系统监控能力
            coordinator_agent = AgentRegistry.get(AgentType.COORDINATOR)
            if coordinator_agent:
                result = await coordinator_agent.process({
                    "action": "monitor",
                    "check_type": "all"
                })
                
                health = result.get("result", {})
                overall_status = health.get("overall_status", "unknown")
                
                status_emoji = {
                    "healthy": "✅", "warning": "⚠️",
                    "critical": "🔴", "unknown": "❓"
                }.get(overall_status, "❓")
                
                lines = [
                    "🖥️ 系统健康状态",
                    f"整体: {status_emoji} {overall_status.upper()}",
                    f"检查时间: {datetime.now(self.CHINA_TZ).strftime('%H:%M')}",
                ]
                
                issues = health.get("issues", [])
                if issues:
                    lines.append("\n⚠️ 问题:")
                    for issue in issues[:5]:
                        lines.append(f"  • {issue}")
                else:
                    lines.append("\n✅ 所有系统运行正常")
                
                return {"success": True, "response": "\n".join(lines)}
            
            return {"success": True, "response": "系统监控服务暂不可用"}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 系统检查失败: {e}")
            return {"success": False, "response": f"系统检查时出错：{str(e)}"}
    
    async def _handle_ai_daily_report(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """生成AI团队日报"""
        await self.log_live_step("think", "生成AI团队日报", "汇总所有AI员工工作数据")
        
        try:
            coordinator_agent = AgentRegistry.get(AgentType.COORDINATOR)
            if coordinator_agent:
                result = await coordinator_agent.process({
                    "action": "report",
                    "report_type": "daily"
                })
                
                readable_report = result.get("readable_report", "报告生成失败")
                
                if len(readable_report) > 2000:
                    readable_report = readable_report[:1950] + "\n...(内容已精简)"
                
                return {"success": True, "response": readable_report}
            
            return {"success": True, "response": "报告服务暂不可用"}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 生成日报失败: {e}")
            return {"success": False, "response": f"生成日报时出错：{str(e)}"}
    
    async def _handle_task_status(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """查询任务状态"""
        await self.log_live_step("search", "查询任务状态", "获取最近任务记录")
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT id, task_type, agent_type, status, 
                               input_data, created_at, completed_at
                        FROM ai_tasks
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                )
                tasks = result.fetchall()
            
            if not tasks:
                context = f"用户问：{message}\n查询结果：目前没有任何任务记录。"
                smart_response = await self.chat(
                    context,
                    "你是郑总的私人助理，在微信上聊天。短句口语，不要用markdown、标签。"
                )
                return {"success": True, "response": smart_response}
            
            agent_names = {v["type"].value: v["name"] for v in self.AGENT_INFO.values()}
            
            status_map = {
                "pending": "等待中", "processing": "进行中",
                "completed": "已完成", "failed": "失败"
            }
            
            task_lines = []
            for task in tasks:
                agent_type = task[2]
                status = task[3]
                input_data = task[4] if isinstance(task[4], dict) else json.loads(task[4] or '{}')
                created_at = task[5]
                
                name = agent_names.get(agent_type, agent_type)
                status_text = status_map.get(status, status)
                desc = input_data.get("description", "无描述")[:50]
                time_str = self.to_china_time(created_at).strftime('%m-%d %H:%M') if created_at else ""
                
                task_lines.append(f"{name}的任务「{desc}」- {status_text}，时间{time_str}")
            
            context = f"""用户问：{message}
最近5条任务记录：
{chr(10).join(task_lines)}"""

            smart_response = await self.chat(
                context,
                "你是郑总的私人助理，在微信上聊天。用口语简要说任务情况，不要用markdown、标签、分隔线。"
            )
            
            return {"success": True, "response": smart_response}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 查询任务状态失败: {e}")
            return {"success": False, "response": f"查询任务状态时出错：{str(e)}"}
    
    # ==================== 文件操作能力（受限） ====================
    
    def _is_path_allowed(self, filepath: str, for_write: bool = False) -> bool:
        """检查文件路径是否在允许范围内"""
        # 检查红区禁令
        for forbidden in self.FORBIDDEN_FILES:
            if forbidden in filepath:
                return False
        
        # 检查绿区许可
        allowed_paths = self.ALLOWED_WRITE_PATHS if for_write else self.ALLOWED_READ_PATHS
        for allowed in allowed_paths:
            if allowed in filepath:
                return True
        
        return False
    
    async def read_agent_file(self, filepath: str) -> Dict[str, Any]:
        """读取AI员工相关文件（受限）"""
        if not self._is_path_allowed(filepath, for_write=False):
            return {
                "success": False,
                "error": f"权限不足：无法读取 {filepath}。此文件属于系统底层架构。"
            }
        
        try:
            # 构建完整路径
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
            return {
                "success": False,
                "error": f"权限不足：无法修改 {filepath}。这个文件属于系统底层。"
            }
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            full_path = os.path.join(base_dir, filepath.replace("backend/", ""))
            
            # 写入前备份
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
            logger.error(f"[Clauwdbot] 写入文件失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_agent_code_modify(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """修改AI员工代码/Prompt - 先出方案，等老板审批后再执行"""
        # 识别目标员工
        target_agent_key = None
        target_agent_name = None
        
        for key, info in self.AGENT_INFO.items():
            if info["name"] in message:
                target_agent_key = key
                target_agent_name = info["name"]
                break
        
        if not target_agent_key:
            return {"success": True, "response": "你要我改哪个员工的代码呀？小调、小影、小文、小销、小跟、小析、小猎、小析2、小欧间谍，说一个就行。"}
        
        # 读取当前 Prompt
        agent = AgentRegistry.get(self.AGENT_INFO[target_agent_key]["type"])
        if not agent:
            return {"success": True, "response": f"{target_agent_name}现在不在线呢。"}
        
        current_prompt = agent.system_prompt or ""
        
        # ===== 第一步：生成修改方案 =====
        modify_prompt = f"""你是一个AI工程师助手。老板要求修改AI员工「{target_agent_name}」的系统Prompt。

老板的要求：{message}

当前Prompt内容（截取前2000字）：
{current_prompt[:2000]}

请根据老板的要求，生成修改后的完整Prompt。注意：
1. 保留员工的核心职责不变
2. 按照老板的要求做针对性修改
3. 保持Prompt的专业性
4. 返回完整的修改后Prompt，不要省略任何部分

只返回修改后的完整Prompt内容，不要加任何说明。"""
        
        try:
            from app.core.llm import chat_completion
            new_prompt = await chat_completion(
                messages=[{"role": "user", "content": modify_prompt}],
                use_advanced=True,
                max_tokens=4000,
                temperature=0.5
            )
            
            # ===== 第二步：生成方案摘要给老板看 =====
            summary_prompt = f"""对比以下两版Prompt的变化，用3-5个要点概括主要改动。
不要贴代码，只说改了什么。简洁直接。

原版核心内容（前500字）：{current_prompt[:500]}
新版核心内容（前500字）：{new_prompt[:500]}

用以下格式：
- 改动1
- 改动2
- 改动3"""
            
            changes_summary = await chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            # ===== 第三步：存储方案，等待审批 =====
            from app.services.memory_service import memory_service
            approval_data = {
                "type": "agent_code_modify",
                "target_agent": target_agent_key,
                "agent_name": target_agent_name,
                "new_prompt": new_prompt,
                "summary": changes_summary,
                "created_at": datetime.now().isoformat()
            }
            await memory_service.remember(
                user_id, "pending_approval",
                json.dumps(approval_data, ensure_ascii=False),
                "workflow"
            )
            
            logger.info(f"[Clauwdbot] 已生成{target_agent_name}修改方案，等待审批")
            
            return {
                "success": True,
                "response": f"好的，我看了一下{target_agent_name}现在的Prompt，给你出个方案：\n\n{changes_summary}\n\n你看行不行？说「通过」我就改。"
            }
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 生成修改方案失败: {e}")
            return {"success": True, "response": f"方案生成的时候出了点问题：{str(e)[:100]}"}
    
    # ==================== 个人助理能力（保留原有） ====================
    
    async def _handle_schedule_add(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理添加日程"""
        await self.log_live_step("think", "解析日程信息", "提取时间、事项、地点")
        
        now = datetime.now()
        weekday_dates = {}
        for i in range(7):
            future_date = now + timedelta(days=i)
            weekday_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][future_date.weekday()]
            if weekday_name not in weekday_dates:
                weekday_dates[weekday_name] = future_date.strftime('%Y-%m-%d')
        
        weekday_info = "\n".join([f"- {k}: {v}" for k, v in weekday_dates.items()])
        today_weekday = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
        
        extract_prompt = f"""从用户消息中提取日程信息，返回JSON格式：

用户消息：{message}
当前时间：{now.strftime('%Y-%m-%d %H:%M')}，今天是{today_weekday}

接下来7天的日期对照表：
{weekday_info}

返回格式：
{{
    "title": "日程标题",
    "start_time": "YYYY-MM-DD HH:MM",
    "end_time": "YYYY-MM-DD HH:MM"（如果没有则为null）,
    "location": "地点"（如果没有则为null）,
    "description": "备注"（如果没有则为null）,
    "priority": "normal"（low/normal/high/urgent）,
    "is_recurring": false,
    "recurring_pattern": null
}}
只返回JSON，不要其他内容。
"""
        
        try:
            response = await self.think([{"role": "user", "content": extract_prompt}], temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"success": False, "response": "抱歉，我没能理解日程信息，请用更清晰的方式告诉我。"}
            
            schedule_data = json.loads(json_match.group())
            
            start_time_str = schedule_data.get("start_time")
            start_time_dt = None
            end_time_dt = None
            
            if start_time_str:
                try:
                    start_time_dt = datetime.fromisoformat(start_time_str)
                except Exception:
                    try:
                        start_time_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
                    except Exception:
                        pass
            
            end_time_str = schedule_data.get("end_time")
            if end_time_str:
                try:
                    end_time_dt = datetime.fromisoformat(end_time_str)
                except Exception:
                    try:
                        end_time_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
                    except Exception:
                        pass
            
            if not start_time_dt:
                return {"success": False, "response": "抱歉，我没能理解日程的时间，请用更清晰的方式告诉我。"}
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO assistant_schedules 
                        (title, description, location, start_time, end_time, priority)
                        VALUES (:title, :description, :location, :start_time, :end_time, :priority)
                        RETURNING id, title, start_time, location
                    """),
                    {
                        "title": schedule_data.get("title", "未命名日程"),
                        "description": schedule_data.get("description"),
                        "location": schedule_data.get("location"),
                        "start_time": start_time_dt,
                        "end_time": end_time_dt,
                        "priority": schedule_data.get("priority", "normal")
                    }
                )
                row = result.fetchone()
                await db.commit()
            
            weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][start_time_dt.weekday()]
            time_str = f"{start_time_dt.month}月{start_time_dt.day}日 {weekday} {start_time_dt.strftime('%H:%M')}"
            location_str = f" 📍{schedule_data['location']}" if schedule_data.get('location') else ""
            
            # 生成 iCal 文件
            ical_path = None
            try:
                ical_path = self._generate_ical_file(
                    title=schedule_data.get("title", "日程"),
                    start_time=start_time_dt,
                    end_time=end_time_dt,
                    location=schedule_data.get("location"),
                    description=schedule_data.get("description"),
                    is_recurring=schedule_data.get("is_recurring", False),
                    recurring_pattern=schedule_data.get("recurring_pattern"),
                )
            except Exception as e:
                logger.warning(f"[Maria] iCal文件生成失败（不影响日程保存）: {e}")
            
            response_text = f"日程已记录：{schedule_data['title']}，{time_str}{location_str}"
            
            result = {"success": True, "response": response_text, "schedule_id": str(row[0])}
            if ical_path:
                result["filepath"] = ical_path
            
            await self.log_result("日程添加成功", schedule_data['title'])
            return result
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 添加日程失败: {e}")
            return {"success": False, "response": f"添加日程时出错了：{str(e)}"}
    
    def _generate_ical_file(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime = None,
        location: str = None,
        description: str = None,
        is_recurring: bool = False,
        recurring_pattern: str = None,
        events: list = None,
    ) -> str:
        """
        生成 iCal (.ics) 文件，返回文件路径。
        
        支持单个事件或批量事件（events 参数）。
        生成的 .ics 文件可以直接导入苹果日历 / Google Calendar / Outlook。
        """
        from icalendar import Calendar, Event, vRecur
        import uuid
        
        cal = Calendar()
        cal.add('prodid', '-//Maria AI Assistant//CN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        
        china_tz = pytz.timezone('Asia/Shanghai')
        
        def _add_event(cal, title, start, end=None, location=None, description=None, recurring=False, pattern=None):
            event = Event()
            event.add('summary', title)
            # 确保有时区信息
            if start.tzinfo is None:
                start = china_tz.localize(start)
            event.add('dtstart', start)
            if end:
                if end.tzinfo is None:
                    end = china_tz.localize(end)
                event.add('dtend', end)
            else:
                event.add('dtend', start + timedelta(hours=1))
            
            if location:
                event.add('location', location)
            if description:
                event.add('description', description)
            
            # 提前15分钟提醒
            from icalendar import Alarm
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', f'提醒：{title}')
            alarm.add('trigger', timedelta(minutes=-15))
            event.add_component(alarm)
            
            # 重复规则
            if recurring and pattern:
                pattern_lower = pattern.lower() if pattern else ""
                if "每周" in pattern_lower or "weekly" in pattern_lower or "每周一" in pattern_lower:
                    # 提取星期几
                    day_map = {"周一": "MO", "周二": "TU", "周三": "WE", "周四": "TH", "周五": "FR", "周六": "SA", "周日": "SU"}
                    days = [v for k, v in day_map.items() if k in pattern]
                    if not days:
                        days = [list(day_map.values())[start.weekday()]]
                    rrule = vRecur({'FREQ': 'WEEKLY', 'BYDAY': days})
                    event.add('rrule', rrule)
                elif "每天" in pattern_lower or "daily" in pattern_lower:
                    event.add('rrule', vRecur({'FREQ': 'DAILY'}))
                elif "每月" in pattern_lower or "monthly" in pattern_lower:
                    event.add('rrule', vRecur({'FREQ': 'MONTHLY'}))
            
            event.add('uid', str(uuid.uuid4()))
            event.add('dtstamp', datetime.now(china_tz))
            cal.add_component(event)
        
        # 批量事件或单个事件
        if events:
            for ev in events:
                _add_event(
                    cal,
                    title=ev.get("title", "日程"),
                    start=ev.get("start_time", start_time),
                    end=ev.get("end_time"),
                    location=ev.get("location"),
                    description=ev.get("description"),
                    recurring=ev.get("is_recurring", False),
                    pattern=ev.get("recurring_pattern"),
                )
        else:
            _add_event(cal, title, start_time, end_time, location, description, is_recurring, recurring_pattern)
        
        # 写入文件
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)[:30]
        filepath = f"/tmp/documents/{safe_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.ics"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            f.write(cal.to_ical())
        
        logger.info(f"[Maria] iCal文件已生成: {filepath}")
        return filepath
    
    async def _handle_schedule_query(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理查询日程"""
        await self.log_live_step("search", "查询日程", "获取相关日程安排")
        
        china_now = datetime.now(self.CHINA_TZ)
        today = china_now.date()
        query_date = today
        date_label = "今天"
        
        # 识别查询日期
        if "明天" in message or "明日" in message:
            query_date = today + timedelta(days=1)
            date_label = "明天"
        elif "后天" in message:
            query_date = today + timedelta(days=2)
            date_label = "后天"
        elif "本周" in message or "这周" in message:
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            return await self._query_schedule_range(start_of_week, end_of_week, "本周")
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT title, start_time, end_time, location, priority, is_completed
                    FROM assistant_schedules
                    WHERE DATE(start_time AT TIME ZONE 'Asia/Shanghai') = :query_date
                    AND is_completed = FALSE
                    ORDER BY start_time ASC
                """),
                {"query_date": query_date}
            )
            schedules = result.fetchall()
        
        # 构造基础数据
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[query_date.weekday()]
        
        raw_data = {
            "date": query_date.strftime('%Y-%m-%d'),
            "weekday": weekday,
            "label": date_label,
            "count": len(schedules),
            "items": [
                {
                    "title": s[0],
                    "time": self.to_china_time(s[1]).strftime("%H:%M"),
                    "location": s[3],
                    "priority": s[4]
                } for s in schedules
            ]
        }

        # 使用 LLM 进行智能回复润色
        context = f"用户询问：{message}\n查询结果：{date_label}({raw_data['date']})共有{len(schedules)}项安排。"
        if schedules:
            items_desc = "\n".join([f"- {i['time']} {i['title']} @ {i['location'] or '无'}" for i in raw_data['items']])
            context += f"\n具体事项：\n{items_desc}"
        else:
            context += "\n目前暂无日程安排。"

        smart_response = await self.chat(
            context, 
            "你是郑总的私人助理，在微信上聊天。短句口语，只说重点，不要用markdown、标签。"
        )
        
        return {"success": True, "response": smart_response}
    
    async def _query_schedule_range(self, start_date, end_date, label: str) -> Dict[str, Any]:
        """查询日期范围内的日程"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT title, start_time, location
                    FROM assistant_schedules
                    WHERE DATE(start_time) BETWEEN :start_date AND :end_date
                    AND is_completed = FALSE
                    ORDER BY start_time ASC
                """),
                {"start_date": start_date, "end_date": end_date}
            )
            schedules = result.fetchall()
        
        if not schedules:
            return {"success": True, "response": f"📅 {label}暂无安排"}
        
        lines = [f"📅 {label}安排", "━" * 18]
        current_date = None
        
        for s in schedules:
            china_time = self.to_china_time(s[1])
            schedule_date = china_time.date()
            if schedule_date != current_date:
                current_date = schedule_date
                weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][schedule_date.weekday()]
                lines.append(f"\n📆 {schedule_date.month}月{schedule_date.day}日 {weekday}")
            
            time_str = china_time.strftime("%H:%M")
            location_str = f" - {s[2]}" if s[2] else ""
            lines.append(f"  {time_str} {s[0]}{location_str}")
        
        lines.append(f"\n共{len(schedules)}项安排")
        
        return {"success": True, "response": "\n".join(lines)}
    
    async def _handle_schedule_cancel(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理取消日程"""
        return {"success": True, "response": "请告诉我要取消哪个日程？比如说'取消明天下午的会议'"}
    
    async def _handle_schedule_update(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理修改日程"""
        await self.log_live_step("think", "解析修改请求", "识别要修改的日程和新信息")
        
        now = datetime.now()
        weekday_dates = {}
        for i in range(7):
            future_date = now + timedelta(days=i)
            weekday_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][future_date.weekday()]
            if weekday_name not in weekday_dates:
                weekday_dates[weekday_name] = future_date.strftime('%Y-%m-%d')
        
        weekday_info = "\n".join([f"- {k}: {v}" for k, v in weekday_dates.items()])
        today_weekday = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
        
        extract_prompt = f"""用户想要修改日程，请分析：

用户消息：{message}
当前时间：{now.strftime('%Y-%m-%d %H:%M')}，今天是{today_weekday}

接下来7天的日期对照表：
{weekday_info}

请返回JSON格式：
{{
    "search_keyword": "用于搜索现有日程的关键词",
    "new_time": "YYYY-MM-DD HH:MM"（新的时间）或 null,
    "new_title": "新标题" 或 null,
    "new_location": "新地点" 或 null
}}
只返回JSON，不要其他内容。
"""
        
        try:
            response = await self.think([{"role": "user", "content": extract_prompt}], temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"success": False, "response": "抱歉，我没能理解您想修改什么，请更详细地描述。"}
            
            update_data = json.loads(json_match.group())
            search_keyword = update_data.get("search_keyword", "")
            
            if not search_keyword:
                return {"success": False, "response": "请告诉我您要修改哪个日程？"}
            
            # 搜索匹配的日程
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT id, title, start_time, location
                        FROM assistant_schedules
                        WHERE title ILIKE :keyword AND is_completed = FALSE
                        ORDER BY start_time ASC LIMIT 5
                    """),
                    {"keyword": f"%{search_keyword}%"}
                )
                schedules = result.fetchall()
            
            if not schedules:
                return {"success": False, "response": f"没有找到'{search_keyword}'相关的日程。"}
            
            schedule = schedules[0]
            schedule_id = schedule[0]
            old_title = schedule[1]
            
            updates = []
            params = {"id": schedule_id}
            
            if update_data.get("new_time"):
                try:
                    new_time = datetime.strptime(update_data["new_time"], "%Y-%m-%d %H:%M")
                    updates.append("start_time = :new_time")
                    params["new_time"] = new_time
                except Exception:
                    pass
            
            if update_data.get("new_title"):
                updates.append("title = :new_title")
                params["new_title"] = update_data["new_title"]
            
            if update_data.get("new_location"):
                updates.append("location = :new_location")
                params["new_location"] = update_data["new_location"]
            
            if not updates:
                return {"success": False, "response": "没有检测到需要修改的内容。"}
            
            updates.append("updated_at = NOW()")
            
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(f"UPDATE assistant_schedules SET {', '.join(updates)} WHERE id = :id"),
                    params
                )
                await db.commit()
            
            changes = []
            if update_data.get("new_time"):
                new_dt = datetime.strptime(update_data["new_time"], "%Y-%m-%d %H:%M")
                weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][new_dt.weekday()]
                changes.append(f"⏰ 时间改为：{new_dt.month}月{new_dt.day}日 {weekday} {new_dt.strftime('%H:%M')}")
            if update_data.get("new_title"):
                changes.append(f"📝 标题改为：{update_data['new_title']}")
            if update_data.get("new_location"):
                changes.append(f"📍 地点改为：{update_data['new_location']}")
            
            response_text = f"""✅ 日程已修改！

📅 {old_title}
{chr(10).join(changes)}

已更新完成。"""
            
            await self.log_result("日程修改成功", old_title)
            return {"success": True, "response": response_text}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 修改日程失败: {e}")
            return {"success": False, "response": f"修改日程时出错了：{str(e)}"}
    
    # ==================== 待办管理 ====================
    
    async def _handle_todo_add(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理添加待办"""
        await self.log_live_step("think", "解析待办信息", "提取内容和截止日期")
        
        extract_prompt = f"""从用户消息中提取待办事项信息，返回JSON格式：

用户消息：{message}
当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

返回格式：
{{
    "content": "待办内容",
    "due_date": "YYYY-MM-DD"（如果有截止日期）或 null,
    "priority": "normal"（low/normal/high/urgent）
}}
只返回JSON，不要其他内容。
"""
        
        try:
            response = await self.think([{"role": "user", "content": extract_prompt}], temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"success": False, "response": "抱歉，我没能理解待办内容，请再说一遍？"}
            
            todo_data = json.loads(json_match.group())
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        INSERT INTO assistant_todos (content, priority, due_date, source_type)
                        VALUES (:content, :priority, :due_date, 'manual')
                        RETURNING id
                    """),
                    {
                        "content": todo_data.get("content", message),
                        "priority": todo_data.get("priority", "normal"),
                        "due_date": todo_data.get("due_date")
                    }
                )
                row = result.fetchone()
                await db.commit()
            
            due_str = ""
            if todo_data.get("due_date"):
                due_date = datetime.strptime(todo_data["due_date"], "%Y-%m-%d")
                due_str = f"\n📆 截止：{due_date.month}月{due_date.day}日"
            
            return {
                "success": True,
                "response": f"✅ 待办已记录！\n\n📋 {todo_data['content']}{due_str}\n\n需要我提醒你吗？",
                "todo_id": str(row[0])
            }
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 添加待办失败: {e}")
            return {"success": False, "response": f"添加待办时出错了：{str(e)}"}
    
    async def _handle_todo_query(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理查询待办"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT content, priority, due_date, created_at
                    FROM assistant_todos
                    WHERE is_completed = FALSE
                    ORDER BY 
                        CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END,
                        due_date ASC NULLS LAST, created_at ASC
                    LIMIT 10
                """)
            )
            todos = result.fetchall()
        
        if not todos:
            return {"success": True, "response": "📋 待办列表\n\n暂无待办事项，真棒！🎉"}
        
        lines = ["📋 待办列表", "━" * 18]
        for i, t in enumerate(todos, 1):
            priority_icon = {"urgent": "🔴", "high": "🟡"}.get(t[1], "")
            due_str = f" (截止{t[2].month}/{t[2].day})" if t[2] else ""
            lines.append(f"{i}. {priority_icon}{t[0]}{due_str}")
        
        lines.append("━" * 18)
        lines.append(f"共{len(todos)}项待办")
        
        return {"success": True, "response": "\n".join(lines)}
    
    async def _handle_todo_complete(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理完成待办"""
        return {"success": True, "response": "请告诉我完成了哪个待办？可以说待办的编号或内容。"}
    
    # ==================== 会议纪要 ====================
    
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
        
        await self.log_live_step("think", "开始语音转写", "这可能需要几分钟时间")
        
        return {
            "success": True,
            "response": "📼 已收到会议录音！\n\n正在处理中，转写完成后会自动发送会议纪要给你。\n\n⏱ 预计需要2-5分钟",
            "meeting_id": str(meeting_id),
            "async_task": "speech_transcription"
        }
    
    async def _handle_meeting_record(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理会议纪要相关请求"""
        return {
            "success": True,
            "response": """📋 会议纪要功能

使用方法：
1. 用手机录制会议
2. 会议结束后，把录音文件发给我
3. 我会自动转写并生成会议纪要

支持格式：mp3、m4a、wav、amr

发送录音文件即可开始~"""
        }
    
    # ==================== 邮件管理 ====================
    
    async def _handle_email_query(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理查询邮件"""
        from app.services.multi_email_service import multi_email_service
        
        await self.log_live_step("search", "查询邮件", "获取未读邮件")
        
        try:
            summary = await multi_email_service.get_unread_summary()
            
            if summary["total_unread"] == 0:
                return {"success": True, "response": "📧 所有邮箱\n\n暂无未读邮件 ✨"}
            
            lines = ["📧 未读邮件汇总", "━" * 18]
            
            for account in summary["accounts"]:
                if account["unread_count"] > 0:
                    lines.append(f"\n📬 {account['name']} ({account['unread_count']}封)")
                    for email in account["recent_emails"][:3]:
                        sender = email["from_name"] or email["from_address"]
                        subject = email["subject"][:20] + "..." if len(email["subject"]) > 20 else email["subject"]
                        lines.append(f"  • {sender}: {subject}")
            
            lines.append("━" * 18)
            lines.append(f"共{summary['total_unread']}封未读")
            
            return {"success": True, "response": "\n".join(lines)}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 查询邮件失败: {e}")
            return {"success": True, "response": "📧 邮件查询暂时不可用，请稍后再试。"}
    
    async def _handle_email_reply(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理回复邮件"""
        return {
            "success": True,
            "response": "请告诉我要回复哪封邮件，以及回复内容是什么？\n\n比如：用工作邮箱回复张总的邮件，说已收到会尽快处理"
        }
    
    # ==================== ERP数据 ====================
    
    async def _handle_erp_query(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理ERP数据查询"""
        from app.services.erp_connector import erp_connector
        
        await self.log_live_step("search", "查询ERP数据", "获取订单和财务信息")
        
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            orders_data = await erp_connector.get_orders(start_date=today, end_date=today, page_size=100)
            total_orders = orders_data.get("total", 0)
            
            try:
                stats = await erp_connector.get_orders_stats()
            except Exception:
                stats = {}
            
            lines = ["📊 今日业务数据", "━" * 18]
            lines.append(f"📦 今日新增订单: {total_orders}单")
            
            if stats:
                lines.append(f"✅ 已完成: {stats.get('completed_today', 0)}单")
                lines.append(f"🔄 进行中: {stats.get('in_progress', 0)}单")
            
            lines.append("━" * 18)
            lines.append("详细数据请登录ERP系统查看")
            
            return {"success": True, "response": "\n".join(lines)}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 查询ERP数据失败: {e}")
            return {"success": True, "response": "📊 ERP数据查询暂时不可用，请检查ERP连接配置。"}
    
    # ==================== 日报汇总 ====================
    
    async def _handle_daily_report(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理每日简报请求"""
        await self.log_live_step("think", "生成每日简报", "汇总日程、订单、邮件、AI团队")
        
        lines = ["📋 今日简报 (by Clauwdbot)", "━" * 18]
        
        # 1. 今日日程
        schedule_result = await self._handle_schedule_query("今天", {}, user_id)
        
        # 2. 待办事项
        todo_result = await self._handle_todo_query("", {}, user_id)
        
        # 3. 订单数据
        try:
            from app.services.erp_connector import erp_connector
            today = datetime.now().strftime("%Y-%m-%d")
            orders_data = await erp_connector.get_orders(start_date=today, end_date=today, page_size=1)
            order_count = orders_data.get("total", 0)
            lines.append(f"\n📦 今日订单: {order_count}单")
        except Exception:
            pass
        
        # 4. 邮件统计
        try:
            from app.services.multi_email_service import multi_email_service
            summary = await multi_email_service.get_unread_summary()
            lines.append(f"📧 未读邮件: {summary['total_unread']}封")
        except Exception:
            pass
        
        # 5. AI团队状态（新增）
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) as total, 
                               COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
                        FROM ai_tasks WHERE created_at >= CURRENT_DATE
                    """)
                )
                task_stats = result.fetchone()
                if task_stats:
                    lines.append(f"🤖 AI团队今日: {task_stats[1]}/{task_stats[0]} 任务完成")
        except Exception:
            pass
        
        return {"success": True, "response": "\n".join(lines)}
    
    # ==================== 帮助 ====================
    
    async def _handle_help(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理帮助请求"""
        context = f"用户问：{message}\n用户想知道Clauwdbot能做什么。"
        smart_response = await self.chat(
            context,
            "你是郑总的私人助理。用户问你能做什么，用聊天的口吻简单说几句就行，不要列清单。比如'我能帮你管团队、记日程、看邮件、写文档、做PPT这些'。"
        )
        return {"success": True, "response": smart_response}
    
    # ==================== 审批流程 ====================
    
    # 通过关键词
    APPROVAL_KEYWORDS = ["同意", "通过", "可以", "行", "好的", "执行", "改吧", "去做吧", "没问题", "ok", "OK", "确认"]
    # 拒绝关键词
    REJECT_KEYWORDS = ["不行", "取消", "算了", "不要", "不改", "先不", "等等", "暂时不"]
    
    async def _check_approval(self, user_id: str, message: str, pending_raw: str) -> Optional[Dict[str, Any]]:
        """
        检查用户消息是否是对待审批方案的回复
        
        Returns:
            处理结果（如果是审批回复），None（如果不是审批相关消息）
        """
        message_stripped = message.strip()
        
        # 检查是否是通过
        is_approve = any(kw in message_stripped for kw in self.APPROVAL_KEYWORDS)
        # 检查是否是拒绝
        is_reject = any(kw in message_stripped for kw in self.REJECT_KEYWORDS)
        
        # 如果既不是通过也不是拒绝，可能是新话题 -> 不处理审批，走正常流程
        if not is_approve and not is_reject:
            # 消息太长（>10字）且不含审批关键词，大概率是新指令
            if len(message_stripped) > 10:
                return None
            # 短消息但不含关键词，也不处理
            return None
        
        try:
            pending_data = json.loads(pending_raw)
        except (json.JSONDecodeError, TypeError):
            # 数据损坏，清除
            from app.services.memory_service import memory_service
            await memory_service.forget(user_id, "pending_approval")
            return None
        
        from app.services.memory_service import memory_service
        
        if is_reject:
            # 拒绝方案
            await memory_service.forget(user_id, "pending_approval")
            return {"success": True, "response": "好的，那先不改了。"}
        
        if is_approve:
            # 通过方案 -> 执行
            result = await self._execute_approved_plan(user_id, pending_data)
            # 清除待审批状态
            await memory_service.forget(user_id, "pending_approval")
            return result
        
        return None
    
    async def _execute_approved_plan(self, user_id: str, plan_data: Dict) -> Dict[str, Any]:
        """执行已审批的方案"""
        plan_type = plan_data.get("type", "")
        
        if plan_type == "agent_code_modify":
            # 修改员工 Prompt
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
                        
                        # 持久化
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
        
        elif plan_type == "agent_upgrade":
            # 升级员工（和 code_modify 类似）
            return await self._execute_approved_plan(user_id, {**plan_data, "type": "agent_code_modify"})
        
        else:
            return {"success": False, "response": "这个方案我不知道怎么执行，你直接告诉我要做什么吧。"}
    
    # ==================== 自我配置能力 ====================
    
    async def _handle_change_name(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """老板要给我改名字 —— 直接改，不废话"""
        # 用 LLM 提取新名字
        extract_prompt = f"""从以下消息中提取用户想给AI助理取的新名字。
用户消息：{message}
只返回名字本身，不要任何其他内容。比如用户说"你以后名字就叫Maria"，你就返回"Maria"。"""
        
        try:
            new_name = await self.think([{"role": "user", "content": extract_prompt}], temperature=0.1)
            new_name = new_name.strip().strip('"').strip("'").strip()
            
            if not new_name or len(new_name) > 20:
                return {"success": True, "response": "你想让我叫什么名字呀？"}
            
            # 保存到记忆系统
            from app.services.memory_service import memory_service
            await memory_service.remember(user_id, "bot_name", new_name, "communication")
            
            # 立即生效
            self._bot_display_name = new_name
            
            logger.info(f"[Clauwdbot] 名字已更改为: {new_name}")
            
            return {
                "success": True,
                "response": f"好呀，以后我就叫{new_name}啦~ 你直接叫我{new_name}就行！"
            }
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 改名失败: {e}")
            return {"success": True, "response": "改名的时候出了点小问题，你再说一遍要叫我什么？"}
    
    # ==================== 专业文档能力 ====================
    
    async def _handle_generate_ppt(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """生成PPT演示文稿"""
        await self.log_live_step("think", "准备生成PPT", "分析主题和要求")
        
        from app.services.document_service import document_service
        
        # 先问清楚需求，再生成
        if len(message) < 15:  # 消息太短，需要更多信息
            context = f"用户说：{message}\n用户想做PPT但信息不够详细。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。他想做PPT但说得不够具体，随意问问主题和大概要几页就行。短句，口语，不要用markdown。"
            )
            return {"success": True, "response": smart_response}
        
        # 信息足够，直接生成
        await self.log_live_step("think", "正在生成PPT", "大约需要30秒")
        
        result = await document_service.generate_ppt(topic=message, requirements="", slides_count=10)
        
        if result.get("success"):
            context = f"PPT已经生成好了，标题是《{result.get('title')}》，一共{result.get('slides_count')}页。文件会自动发送到聊天窗口。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。PPT做好了已经发过去了，简单说一句标题和页数，问要不要改。绝对不要提文件路径。短句口语。"
            )
            return {"success": True, "response": smart_response, "file": result.get("filepath")}
        else:
            return {"success": False, "response": f"郑总，PPT生成遇到了点问题：{result.get('error')}。要不我换个方式帮您试试？"}
    
    async def _handle_generate_word(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """生成Word文档（计划书/方案/报告）"""
        await self.log_live_step("think", "准备生成文档", "分析主题和要求")
        
        from app.services.document_service import document_service
        
        if len(message) < 10:
            context = f"用户说：{message}\n用户想写文档但信息不够。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。他想写文档但信息不够，随意问问写什么主题、大概什么方向就行。短句口语，不要用markdown。"
            )
            return {"success": True, "response": smart_response}
        
        await self.log_live_step("think", "正在撰写文档", "大约需要1分钟")
        
        result = await document_service.generate_word(topic=message)
        
        if result.get("success"):
            context = f"Word文档已经写好了，标题是《{result.get('title')}》，一共{result.get('sections_count')}个章节。文件会自动发送到聊天窗口。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。文档写好了已经发过去了，简单说一句标题和大概内容，问要不要改。绝对不要提文件路径。短句口语。"
            )
            return {"success": True, "response": smart_response, "file": result.get("filepath")}
        else:
            return {"success": False, "response": f"郑总，文档生成遇到了点问题：{result.get('error')}。我再帮您试试~"}
    
    async def _handle_generate_code(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """帮老板写代码"""
        await self.log_live_step("think", "分析代码需求", "准备编写代码")
        
        from app.services.document_service import document_service
        
        if len(message) < 10:
            context = f"用户说：{message}\n用户想写代码但需求不清楚。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。他想写代码但没说清楚要什么，问问想实现什么功能就行。短句口语。"
            )
            return {"success": True, "response": smart_response}
        
        # 判断语言
        language = "python"
        if any(kw in message.lower() for kw in ["javascript", "js", "前端", "react", "vue"]):
            language = "javascript"
        elif any(kw in message.lower() for kw in ["sql", "数据库", "查询"]):
            language = "sql"
        
        result = await document_service.generate_code(requirement=message, language=language)
        
        if result.get("success"):
            return {"success": True, "response": result["code"]}
        else:
            return {"success": False, "response": f"郑总，代码写的时候遇到了点问题，我再试一下~"}
    
    # ==================== 邮件深度阅读（新增）====================
    
    async def _handle_email_deep_read(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """深度阅读邮件 - 分类、摘要、建议"""
        await self.log_live_step("search", "深度分析邮件", "正在阅读所有未读邮件")
        
        try:
            from app.services.multi_email_service import multi_email_service
            from app.services.email_ai_service import email_ai_service
            
            # 获取未读邮件
            summary = await multi_email_service.get_unread_summary()
            
            if summary.get("total_unread", 0) == 0:
                return {"success": True, "response": "郑总，邮箱里没有新邮件呢，挺清净的~"}
            
            # 收集所有未读邮件
            all_emails = []
            for account in summary.get("accounts", []):
                for email in account.get("recent_emails", []):
                    all_emails.append({
                        "from": email.get("from_name") or email.get("from_address", ""),
                        "subject": email.get("subject", ""),
                        "body": email.get("body_preview", ""),
                        "date": email.get("date", "")
                    })
            
            # AI 深度分析
            brief = await email_ai_service.generate_daily_email_brief(all_emails)
            
            return {"success": True, "response": brief}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 邮件深度阅读失败: {e}")
            return {"success": True, "response": "郑总，邮件服务暂时连不上，我稍后帮您重试一下~"}
    
    # ==================== 工作总结（新增）====================
    
    async def _handle_daily_summary(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """生成日报/今日总结"""
        await self.log_live_step("think", "汇总今日数据", "正在生成工作总结")
        
        try:
            from app.services.summary_service import summary_service
            
            summary = await summary_service.generate_daily_summary()
            return {"success": True, "response": summary}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 日报生成失败: {e}")
            return {"success": True, "response": "郑总，今日数据还在汇总中，我整理好了发给您~"}
    
    async def _handle_weekly_summary(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """生成周报"""
        await self.log_live_step("think", "汇总一周数据", "正在生成周报")
        
        try:
            from app.services.summary_service import summary_service
            
            summary = await summary_service.generate_weekly_summary()
            return {"success": True, "response": summary}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 周报生成失败: {e}")
            return {"success": True, "response": "郑总，这周的数据还在汇总中，我整理好了发给您~"}
    
    # ==================== 邮件管理（增强版）====================

    async def _handle_send_email(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """通过指定邮箱发送邮件"""
        from app.services.multi_email_service import multi_email_service
        
        to_emails = args.get("to_emails", [])
        subject = args.get("subject", "")
        body = args.get("body", "")
        account_name = args.get("account_name")
        
        if not to_emails or not subject or not body:
            return {"status": "error", "message": "收件人、主题、正文都不能为空"}
        
        try:
            # 找到要用的邮箱账户
            accounts = await multi_email_service.get_email_accounts()
            if not accounts:
                return {"status": "error", "message": "还没有配置邮箱，请先添加一个邮箱账户"}
            
            target_account = None
            if account_name:
                # 按名称匹配
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target_account = acc
                        break
            
            if not target_account:
                # 用默认邮箱或第一个
                target_account = next((a for a in accounts if a.get("is_default")), accounts[0])
            
            # 构建HTML邮件正文
            body_html = body.replace("\n", "<br>")
            
            result = await multi_email_service.send_email(
                account_id=target_account["id"],
                to_emails=to_emails,
                subject=subject,
                body_html=body_html,
                body_text=body,
            )
            
            if result.get("success"):
                return {
                    "status": "success",
                    "message": f"邮件已通过 {target_account['email_address']} 发送给 {', '.join(to_emails)}",
                    "from_account": target_account["email_address"],
                }
            else:
                return {"status": "error", "message": f"发送失败: {result.get('error', '未知错误')}"}
                
        except Exception as e:
            logger.error(f"[Maria] 发送邮件失败: {e}")
            return {"status": "error", "message": f"发送邮件出错: {str(e)}"}

    async def _handle_sync_emails(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """同步邮箱邮件"""
        from app.services.multi_email_service import multi_email_service
        
        account_name = args.get("account_name")
        
        try:
            if account_name:
                # 同步指定邮箱
                accounts = await multi_email_service.get_email_accounts()
                target = None
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target = acc
                        break
                
                if not target:
                    return {"status": "error", "message": f"没找到名为 '{account_name}' 的邮箱"}
                
                result = await multi_email_service.sync_account_emails(target["id"])
                if result.get("success"):
                    return {
                        "status": "success",
                        "message": f"{target['name']} 同步完成，新增 {result.get('new_count', 0)} 封邮件",
                        "new_count": result.get("new_count", 0),
                    }
                else:
                    return {"status": "error", "message": f"同步失败: {result.get('error', '')}"}
            else:
                # 同步所有邮箱
                result = await multi_email_service.sync_all_accounts()
                total_new = sum(
                    r["result"].get("new_count", 0)
                    for r in result.get("results", [])
                    if r["result"].get("success")
                )
                return {
                    "status": "success",
                    "message": f"已同步 {result['total_accounts']} 个邮箱，共新增 {total_new} 封邮件",
                    "total_new": total_new,
                    "accounts_synced": result["total_accounts"],
                }
                
        except Exception as e:
            logger.error(f"[Maria] 同步邮件失败: {e}")
            return {"status": "error", "message": f"同步出错: {str(e)}"}

    async def _handle_manage_email_account(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """管理邮箱账户（添加/查看/删除/测试）"""
        from app.services.multi_email_service import multi_email_service
        
        action = args.get("action", "list")
        
        try:
            if action == "list":
                accounts = await multi_email_service.get_email_accounts(active_only=False)
                if not accounts:
                    return {"status": "success", "message": "还没有配置任何邮箱", "accounts": []}
                
                account_list = []
                for acc in accounts:
                    account_list.append({
                        "name": acc["name"],
                        "email": acc["email_address"],
                        "provider": acc["provider"],
                        "sync_enabled": acc["sync_enabled"],
                        "is_default": acc.get("is_default", False),
                    })
                return {
                    "status": "success",
                    "message": f"共有 {len(accounts)} 个邮箱账户",
                    "accounts": account_list,
                }
            
            elif action == "add":
                name = args.get("name", "")
                email_address = args.get("email_address", "")
                password = args.get("password", "")
                provider = args.get("provider", "other")
                
                if not email_address or not password:
                    return {"status": "error", "message": "添加邮箱需要提供邮箱地址和密码"}
                
                if not name:
                    name = email_address.split("@")[0] + "邮箱"
                
                result = await multi_email_service.add_email_account(
                    name=name,
                    email_address=email_address,
                    provider=provider,
                    imap_password=password,
                    smtp_password=password,
                )
                
                if result.get("success"):
                    # 启用同步
                    await multi_email_service.update_email_account(
                        result["account_id"], sync_enabled=True
                    )
                    return {
                        "status": "success",
                        "message": f"邮箱 {email_address} ({name}) 添加成功，已启用自动同步",
                        "account_id": result["account_id"],
                    }
                else:
                    return {"status": "error", "message": f"添加失败: {result.get('error', '')}"}
            
            elif action == "delete":
                account_name = args.get("account_name", "")
                if not account_name:
                    return {"status": "error", "message": "请指定要删除的邮箱名称"}
                
                accounts = await multi_email_service.get_email_accounts(active_only=False)
                target = None
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target = acc
                        break
                
                if not target:
                    return {"status": "error", "message": f"没找到名为 '{account_name}' 的邮箱"}
                
                await multi_email_service.delete_email_account(target["id"])
                return {"status": "success", "message": f"邮箱 {target['email_address']} 已删除"}
            
            elif action == "test":
                account_name = args.get("account_name", "")
                accounts = await multi_email_service.get_email_accounts()
                target = None
                for acc in accounts:
                    if account_name.lower() in acc["name"].lower() or account_name.lower() in acc["email_address"].lower():
                        target = acc
                        break
                
                if not target:
                    return {"status": "error", "message": f"没找到名为 '{account_name}' 的邮箱"}
                
                result = await multi_email_service.test_email_account(target["id"])
                if result.get("success"):
                    return {"status": "success", "message": f"邮箱 {target['email_address']} 连接正常（收发都OK）"}
                else:
                    imap_ok = result.get("imap", {}).get("success", False)
                    smtp_ok = result.get("smtp", {}).get("success", False)
                    issues = []
                    if not imap_ok:
                        issues.append(f"收件(IMAP)失败: {result.get('imap', {}).get('error', '')}")
                    if not smtp_ok:
                        issues.append(f"发件(SMTP)失败: {result.get('smtp', {}).get('error', '')}")
                    return {"status": "error", "message": f"邮箱连接有问题: {'; '.join(issues)}"}
            
            else:
                return {"status": "error", "message": f"未知操作: {action}"}
                
        except Exception as e:
            logger.error(f"[Maria] 邮箱管理操作失败: {e}")
            return {"status": "error", "message": f"操作失败: {str(e)}"}

    # ==================== 苹果日历直写 ====================

    async def _handle_add_to_apple_calendar(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        直接往老板的苹果日历里写入事件（通过 CalDAV）
        """
        from app.services.caldav_service import apple_calendar
        
        events_raw = args.get("events", [])
        if not events_raw:
            return {"status": "error", "message": "没有提供日程事件"}
        
        # 解析事件
        events = []
        for ev in events_raw:
            start_str = ev.get("start_date", "")
            start_dt = None
            end_dt = None
            
            # 解析开始时间
            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]:
                try:
                    start_dt = datetime.strptime(start_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not start_dt:
                logger.warning(f"[Maria] 日程时间解析失败: {start_str}")
                continue
            
            # 解析结束时间
            end_str = ev.get("end_date")
            if end_str:
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]:
                    try:
                        end_dt = datetime.strptime(end_str, fmt)
                        break
                    except ValueError:
                        continue
            
            events.append({
                "title": ev.get("title", "日程"),
                "start_time": start_dt,
                "end_time": end_dt,
                "location": ev.get("location"),
                "description": ev.get("description"),
                "alarm_minutes": ev.get("alarm_minutes", 15),
                "is_recurring": ev.get("is_recurring", False),
                "recurring_pattern": ev.get("recurring_pattern"),
            })
        
        if not events:
            return {"status": "error", "message": "日程时间解析失败，请检查日期格式"}
        
        try:
            result = await apple_calendar.add_events(events)
            logger.info(f"[Maria] 苹果日历写入结果: {result['message']}")
            return result
        except Exception as e:
            logger.error(f"[Maria] 苹果日历写入失败: {e}")
            return {"status": "error", "message": f"写入苹果日历失败: {str(e)}"}

    # ==================== 联网搜索 ====================

    async def _handle_web_search(self, query: str, search_type: str = "search", num_results: int = 5) -> Dict[str, Any]:
        """
        通过 Serper API 搜索 Google
        
        Args:
            query: 搜索关键词
            search_type: "search"=网页搜索, "news"=新闻搜索
            num_results: 返回结果数量(1-10)
        """
        from app.core.config import settings
        import httpx
        
        api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not api_key:
            return {"status": "error", "message": "搜索服务暂不可用（API未配置）"}
        
        # 选择搜索端点
        endpoint = "https://google.serper.dev/news" if search_type == "news" else "https://google.serper.dev/search"
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "X-API-KEY": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "gl": "cn",
                        "hl": "zh-cn",
                        "num": min(num_results, 10)
                    }
                )
                
                if response.status_code != 200:
                    return {"status": "error", "message": f"搜索请求失败（HTTP {response.status_code}）"}
                
                data = response.json()
                
                # 解析搜索结果
                results = []
                source_key = "news" if search_type == "news" else "organic"
                
                for item in data.get(source_key, [])[:num_results]:
                    result_item = {
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", "") or item.get("description", ""),
                        "url": item.get("link", "") or item.get("url", ""),
                    }
                    if search_type == "news":
                        result_item["source"] = item.get("source", "")
                        result_item["date"] = item.get("date", "")
                    results.append(result_item)
                
                # 额外信息
                answer_box = data.get("answerBox", {})
                knowledge_graph = data.get("knowledgeGraph", {})
                
                summary_parts = []
                if answer_box:
                    summary_parts.append(f"快速答案: {answer_box.get('answer', '') or answer_box.get('snippet', '')}")
                if knowledge_graph:
                    kg_desc = knowledge_graph.get("description", "")
                    if kg_desc:
                        summary_parts.append(f"知识摘要: {kg_desc}")
                
                return {
                    "status": "success",
                    "query": query,
                    "result_count": len(results),
                    "results": results,
                    "quick_answer": "\n".join(summary_parts) if summary_parts else None,
                    "message": f"搜索到 {len(results)} 条结果"
                }
                
        except httpx.TimeoutException:
            return {"status": "error", "message": "搜索超时，请稍后再试"}
        except Exception as e:
            logger.error(f"[Maria] 搜索失败: {e}")
            return {"status": "error", "message": f"搜索出错: {str(e)}"}

    async def _handle_fetch_webpage(self, url: str) -> Dict[str, Any]:
        """
        抓取网页内容并提取正文
        
        Args:
            url: 目标网页URL
        """
        import httpx
        
        if not url or not url.startswith(("http://", "https://")):
            return {"status": "error", "message": "无效的网址"}
        
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            ) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return {"status": "error", "message": f"无法访问该网页（HTTP {response.status_code}）"}
                
                html = response.text
                
                # 用 BeautifulSoup 提取正文
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # 移除不需要的标签
                    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]):
                        tag.decompose()
                    
                    # 获取标题
                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    
                    # 获取正文
                    text = soup.get_text(separator="\n", strip=True)
                    
                    # 清理多余空行
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    clean_text = "\n".join(lines)
                    
                    # 限制字符数，防止token爆炸
                    max_chars = 3000
                    if len(clean_text) > max_chars:
                        clean_text = clean_text[:max_chars] + "\n...(内容已截断)"
                    
                    return {
                        "status": "success",
                        "url": url,
                        "title": title,
                        "content": clean_text,
                        "content_length": len(clean_text),
                        "message": f"已抓取网页内容（{len(clean_text)}字）"
                    }
                    
                except ImportError:
                    # 没有 beautifulsoup4，用简单正则提取
                    import re
                    text = re.sub(r'<[^>]+>', ' ', html)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if len(text) > 3000:
                        text = text[:3000] + "...(已截断)"
                    return {
                        "status": "success",
                        "url": url,
                        "title": "",
                        "content": text,
                        "content_length": len(text),
                        "message": f"已抓取网页内容（{len(text)}字）"
                    }
                
        except httpx.TimeoutException:
            return {"status": "error", "message": "网页加载超时"}
        except Exception as e:
            logger.error(f"[Maria] 抓取网页失败: {e}")
            return {"status": "error", "message": f"抓取失败: {str(e)}"}

    async def _handle_unknown(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理无法识别的意图 - 带对话上下文的AI智能回复"""
        # 构建对话上下文
        recent_history = getattr(self, '_recent_history', [])
        
        # 用 messages 数组传给 LLM，保持对话连贯
        messages = []
        system_msg = "你是郑总的私人助理，在微信上聊天。短句口语，说重点就好，不要用markdown、标签、分隔线。你能管理AI员工团队、操作日程、待办、邮件和ERP。直接回答问题，不要说你无法做什么。"
        messages.append({"role": "system", "content": system_msg})
        
        # 注入最近对话历史
        for msg in recent_history[-8:]:
            messages.append({"role": msg["role"], "content": msg["content"][:300]})
        
        # 当前用户消息
        messages.append({"role": "user", "content": message})
        
        try:
            from app.core.llm import chat_completion
            response = await chat_completion(
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )
            return {"success": True, "response": response}
        except Exception as e:
            logger.error(f"[Clauwdbot] 对话回复失败: {e}")
            # 降级：无上下文直接回复
            response = await self.chat(message, system_msg)
            return {"success": True, "response": response}
    
    # ==================== 工具方法 ====================
    
    async def _load_recent_history(self, user_id: str, limit: int = 6) -> List[Dict]:
        """
        加载最近的对话历史（用于上下文理解）
        返回: [{"role": "user"/"assistant", "content": "..."}]
        """
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
            
            # 倒序还原（从旧到新）
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
        lines = [f"📅 明日安排预览（{tomorrow.month}月{tomorrow.day}日 {weekday}）", "━" * 18]
        
        for s in schedules:
            china_time = self.to_china_time(s[1])
            time_str = china_time.strftime("%H:%M")
            location_str = f" - {s[2]}" if s[2] else ""
            priority_icon = {"urgent": "🔴", "high": "🟡"}.get(s[3], "")
            lines.append(f"{time_str} {priority_icon}{s[0]}{location_str}")
        
        lines.append("━" * 18)
        lines.append(f"共{len(schedules)}项安排，请做好准备！")
        
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
