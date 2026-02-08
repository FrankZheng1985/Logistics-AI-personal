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
        "lead_hunter": {"name": "小猎", "type": AgentType.LEAD_HUNTER, "prompt_file": None},
        "analyst2": {"name": "小析2", "type": AgentType.ANALYST2, "prompt_file": None},
        "eu_customs_monitor": {"name": "小欧间谍", "type": AgentType.EU_CUSTOMS_MONITOR, "prompt_file": None},
    }
    
    # 意图分类（扩展版，增加管理类意图）
    INTENT_TYPES = {
        # === 管理类意图（新增）===
        "agent_status": ["团队状态", "员工状态", "AI状态", "谁在工作", "工作情况"],
        "agent_dispatch": ["让小", "安排小", "派小", "叫小", "通知小"],
        "agent_upgrade": ["优化", "升级", "改进", "修改prompt", "修改提示词", "调整风格"],
        "agent_code_read": ["看一下代码", "查看代码", "读取代码", "代码逻辑"],
        "system_status": ["系统状态", "健康检查", "系统健康"],
        "daily_report_ai": ["日报", "报告", "工作汇报", "今日汇报"],
        "task_status": ["任务状态", "进度", "完成了吗", "怎么样了"],
        # === 个人助理意图（保留原有）===
        "schedule_query": ["有什么安排", "有什么会", "查看日程", "查询日程", "今天安排", "明天安排", "今天有", "明天有", "日程", "行程"],
        "schedule_update": ["修改", "改成", "改为", "调整时间", "更改", "变更日程"],
        "schedule_cancel": ["取消", "删除日程", "不开了"],
        "schedule_add": ["记住", "记录", "添加日程", "提醒我", "帮我记"],
        "todo_query": ["待办列表", "还有什么没做", "待办事项"],
        "todo_complete": ["完成了", "做完了", "搞定了"],
        "todo_add": ["待办", "要做", "记得做", "别忘了"],
        "meeting_record": ["会议纪要", "整理会议", "会议结束"],
        "email_query": ["邮件", "收件箱", "新邮件", "查看邮件"],
        "email_reply": ["回复邮件", "发邮件"],
        "erp_query": ["订单", "今天多少单", "财务", "营收"],
        "report": ["简报", "今日总结"],
        "help": ["帮助", "你能做什么", "功能"],
    }
    
    @staticmethod
    def to_china_time(dt):
        """转换为中国时区时间"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(ClauwdbotAgent.CHINA_TZ)
    
    def _build_system_prompt(self) -> str:
        return CLAUWDBOT_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户消息 - Clauwdbot超级助理
        
        Args:
            input_data: {
                "message": 用户消息内容,
                "user_id": 企业微信用户ID,
                "message_type": text/voice/file,
                "file_url": 文件URL（如果是语音/文件）
            }
        """
        message = input_data.get("message", "")
        user_id = input_data.get("user_id", "")
        message_type = input_data.get("message_type", "text")
        file_url = input_data.get("file_url")
        
        await self.start_task_session("process_message", f"Clauwdbot处理消息: {message[:50]}...")
        
        try:
            # 1. 如果是语音/文件消息，处理录音
            if message_type in ["voice", "file"] and file_url:
                await self.log_live_step("think", "收到音频文件", "准备进行会议录音转写")
                result = await self._handle_audio_file(file_url, user_id)
                await self.end_task_session("会议录音处理完成")
                return result
            
            # 2. 解析用户意图
            await self.log_live_step("think", "Clauwdbot分析指令", message[:100])
            intent = await self._parse_intent(message)
            
            # 3. 根据意图处理
            handler_map = {
                # === 管理类处理器 ===
                "agent_status": self._handle_agent_status,
                "agent_dispatch": self._handle_agent_dispatch,
                "agent_upgrade": self._handle_agent_upgrade,
                "agent_code_read": self._handle_agent_code_read,
                "system_status": self._handle_system_status,
                "daily_report_ai": self._handle_ai_daily_report,
                "task_status": self._handle_task_status,
                # === 个人助理处理器 ===
                "schedule_add": self._handle_schedule_add,
                "schedule_update": self._handle_schedule_update,
                "schedule_query": self._handle_schedule_query,
                "schedule_cancel": self._handle_schedule_cancel,
                "todo_add": self._handle_todo_add,
                "todo_query": self._handle_todo_query,
                "todo_complete": self._handle_todo_complete,
                "meeting_record": self._handle_meeting_record,
                "email_query": self._handle_email_query,
                "email_reply": self._handle_email_reply,
                "erp_query": self._handle_erp_query,
                "report": self._handle_daily_report,
                "help": self._handle_help,
            }
            
            handler = handler_map.get(intent["type"], self._handle_unknown)
            result = await handler(message, intent, user_id)
            
            # 4. 记录交互
            await self._save_interaction(user_id, message, message_type, intent, result.get("response", ""))
            
            await self.end_task_session(f"处理完成: {intent['type']}")
            return result
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 处理消息失败: {e}")
            await self.log_error(str(e))
            await self.end_task_session(error_message=str(e))
            return {
                "success": False,
                "response": "老板，处理您的请求时出现了问题，请稍后再试。",
                "error": str(e)
            }
    
    async def _parse_intent(self, message: str) -> Dict[str, Any]:
        """解析用户意图（增强版：支持管理类指令）"""
        message_lower = message.lower()
        
        # 先用关键词匹配
        best_match = None
        best_length = 0
        
        for intent_type, keywords in self.INTENT_TYPES.items():
            for keyword in keywords:
                if keyword in message_lower and len(keyword) > best_length:
                    best_match = {"type": intent_type, "confidence": 0.8, "keyword": keyword}
                    best_length = len(keyword)
        
        if best_match:
            return best_match
        
        # 关键词匹配失败，使用AI分析
        analysis_prompt = f"""分析用户消息的意图，返回JSON格式：

用户消息：{message}

可能的意图类型：
【管理类】
- agent_status: 查看AI团队/员工状态
- agent_dispatch: 让某个AI员工执行任务（如"让小猎搜索XXX"）
- agent_upgrade: 优化/升级某个AI员工的能力或Prompt
- agent_code_read: 查看AI员工的代码逻辑
- system_status: 系统状态检查
- daily_report_ai: AI团队日报/工作报告
- task_status: 查询任务进度

【个人助理类】
- schedule_add: 添加新日程/安排
- schedule_update: 修改现有日程
- schedule_query: 查询日程
- schedule_cancel: 取消日程
- todo_add: 添加待办事项
- todo_query: 查询待办
- todo_complete: 完成待办
- meeting_record: 会议纪要相关
- email_query: 查询邮件
- email_reply: 回复/发送邮件
- erp_query: 查询订单/财务数据
- report: 每日简报
- help: 帮助
- unknown: 无法识别

返回格式：{{"type": "xxx", "confidence": 0.9, "extracted": {{"target": "...", "content": "..."}}}}
只返回JSON，不要其他内容。
"""
        
        try:
            response = await self.think([{"role": "user", "content": analysis_prompt}], temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"[Clauwdbot] AI意图分析失败: {e}")
        
        return {"type": "unknown", "confidence": 0.5}
    
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
                        SELECT agent_type, agent_name, status, tasks_completed_today, 
                               total_tasks_completed, last_active_at
                        FROM ai_agents
                        ORDER BY agent_type
                    """)
                )
                agents = agent_result.fetchall()
            
            lines = ["🤖 AI团队状态报告", "━" * 18]
            
            # 显示已注册的AI员工
            if agents:
                for agent in agents:
                    status_icon = "🟢" if agent[2] == "active" else "🔴"
                    lines.append(f"{status_icon} {agent[1]} | 今日: {agent[3]}任务 | 总计: {agent[4]}")
            
            # 显示今日任务统计
            if stats:
                lines.append("")
                lines.append("📊 今日任务统计")
                lines.append("━" * 18)
                
                agent_names = {v["type"].value: v["name"] for v in self.AGENT_INFO.values()}
                
                for row in stats:
                    agent_type = row[0]
                    total = row[1]
                    completed = row[2]
                    failed = row[3]
                    in_progress = row[4]
                    
                    name = agent_names.get(agent_type, agent_type)
                    success_rate = (completed / total * 100) if total > 0 else 0
                    status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "🔴"
                    
                    lines.append(f"{status_emoji} {name}: {completed}/{total}完成 ({success_rate:.0f}%)")
                    if in_progress > 0:
                        lines.append(f"   🔄 进行中: {in_progress}")
            else:
                lines.append("")
                lines.append("今日暂无任务记录")
            
            lines.append("")
            lines.append(f"📅 {datetime.now(self.CHINA_TZ).strftime('%Y-%m-%d %H:%M')}")
            
            return {"success": True, "response": "\n".join(lines)}
            
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
            suggestion = await self.think([{"role": "user", "content": upgrade_prompt}], temperature=0.7)
            
            # 截取适合企业微信的长度
            if len(suggestion) > 1500:
                suggestion = suggestion[:1500] + "\n...(方案较长已截取)"
            
            response_text = f"""🔧 {target_agent_name}升级方案

📋 优化建议：
{suggestion}

⚠️ 确认后我会修改{target_agent_name}的Prompt。
请回复「确认升级」执行，或「取消」放弃。"""
            
            return {
                "success": True,
                "response": response_text,
                "upgrade_data": {
                    "target_agent": target_agent_key,
                    "suggestion": suggestion
                }
            }
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 生成升级方案失败: {e}")
            return {"success": False, "response": f"生成升级方案时出错：{str(e)}"}
    
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
                return {"success": True, "response": "📋 暂无任务记录"}
            
            agent_names = {v["type"].value: v["name"] for v in self.AGENT_INFO.values()}
            
            status_emoji = {
                "pending": "⏳", "processing": "🔄",
                "completed": "✅", "failed": "❌"
            }
            
            lines = ["📋 最近任务状态", "━" * 18]
            
            for task in tasks:
                task_id = str(task[0])[:8]
                agent_type = task[2]
                status = task[3]
                input_data = task[4] if isinstance(task[4], dict) else json.loads(task[4] or '{}')
                created_at = task[5]
                
                name = agent_names.get(agent_type, agent_type)
                emoji = status_emoji.get(status, "❓")
                desc = input_data.get("description", "")[:30]
                time_str = self.to_china_time(created_at).strftime('%m-%d %H:%M') if created_at else ""
                
                lines.append(f"{emoji} [{task_id}] {desc}")
                lines.append(f"   {name} | {status} | {time_str}")
            
            return {"success": True, "response": "\n".join(lines)}
            
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
            
            response_text = f"""✅ 日程已记录！

📅 {schedule_data['title']}
⏰ {time_str}{location_str}

我会提前提醒你的。"""
            
            await self.log_result("日程添加成功", schedule_data['title'])
            return {"success": True, "response": response_text, "schedule_id": str(row[0])}
            
        except Exception as e:
            logger.error(f"[Clauwdbot] 添加日程失败: {e}")
            return {"success": False, "response": f"添加日程时出错了：{str(e)}"}
    
    async def _handle_schedule_query(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理查询日程"""
        await self.log_live_step("search", "查询日程", "获取相关日程安排")
        
        china_now = datetime.now(self.CHINA_TZ)
        today = china_now.date()
        query_date = today
        date_label = "今天"
        
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
        
        if not schedules:
            weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][query_date.weekday()]
            return {
                "success": True,
                "response": f"📅 {date_label}（{query_date.month}月{query_date.day}日 {weekday}）\n\n暂无安排，可以好好休息~"
            }
        
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][query_date.weekday()]
        lines = [f"📅 {date_label}安排（{query_date.month}月{query_date.day}日 {weekday}）", "━" * 18]
        
        for s in schedules:
            china_time = self.to_china_time(s[1])
            time_str = china_time.strftime("%H:%M")
            location_str = f" - {s[3]}" if s[3] else ""
            priority_icon = {"urgent": "🔴", "high": "🟡"}.get(s[4], "")
            lines.append(f"{time_str} {priority_icon}{s[0]}{location_str}")
        
        lines.append("━" * 18)
        lines.append(f"共{len(schedules)}项安排")
        
        return {"success": True, "response": "\n".join(lines)}
    
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
        return {
            "success": True,
            "response": """🤖 我是Clauwdbot，AI中心超级助理

🔧 **AI团队管理**
• "团队状态" - 查看AI员工工作情况
• "让小猎搜索XXX" - 分配任务
• "优化小文的写作风格" - 升级AI员工
• "系统状态" - 健康检查
• "日报" - AI团队工作报告

📅 **日程管理**
• "明天下午3点和张总开会"
• "今天有什么安排"

📋 **待办事项**
• "记得下周五交报告"
• "待办列表"

📼 **会议纪要**
• 发送会议录音给我

📧 **邮件** / 📊 **ERP数据**
• "查看新邮件" / "今天订单情况"

有什么需要帮忙的？"""
        }
    
    async def _handle_unknown(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理无法识别的意图 - 使用AI智能回复"""
        response = await self.chat(message, "用户向你咨询，请以Clauwdbot的身份简洁回答或引导他使用你的功能")
        return {"success": True, "response": response}
    
    # ==================== 工具方法 ====================
    
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
