"""
TeamManagementSkill - AI团队管理技能

职责：
- 查看AI团队状态
- 分配任务给AI员工
- 升级AI员工Prompt
- 读取AI员工代码
- 系统状态检查
- AI日报生成
- 任务状态查询
"""
import json
import re
import uuid
from datetime import datetime
from typing import Dict, Any, List

from loguru import logger
from sqlalchemy import text

from app.skills.base import BaseSkill, SkillRegistry
from app.models.database import AsyncSessionLocal
from app.models.conversation import AgentType
from app.agents.base import AgentRegistry
from app.core.prompts.clauwdbot import AGENT_UPGRADE_PROMPT
import pytz


CHINA_TZ = pytz.timezone('Asia/Shanghai')

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


class TeamManagementSkill(BaseSkill):
    """AI团队管理技能"""

    name = "team_management"
    description = "管理AI员工团队：查看状态、分配任务、升级能力、查看代码、系统检查"
    tool_names = [
        "check_agent_status",
        "dispatch_agent_task",
        "upgrade_agent",
        "read_agent_code",
        "modify_agent_code",
        "check_system_status",
        "generate_ai_report",
        "check_task_status",
    ]

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        """路由到具体处理方法"""
        handlers = {
            "check_agent_status": self._handle_agent_status,
            "dispatch_agent_task": self._handle_agent_dispatch,
            "upgrade_agent": self._handle_agent_upgrade,
            "read_agent_code": self._handle_agent_code_read,
            "modify_agent_code": self._handle_agent_upgrade,  # 复用升级流程
            "check_system_status": self._handle_system_status,
            "generate_ai_report": self._handle_ai_daily_report,
            "check_task_status": self._handle_task_status,
        }
        handler = handlers.get(tool_name)
        if handler:
            return await handler(message=message, intent={}, user_id=user_id, args=args)
        return self._err(f"未知工具: {tool_name}")

    # ==================== 团队状态 ====================

    async def _handle_agent_status(self, message: str, intent: Dict, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """查看AI团队工作状态"""
        await self.log_step("search", "查询AI团队状态", "获取所有AI员工今日工作数据")

        try:
            async with AsyncSessionLocal() as db:
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

                agent_result = await db.execute(
                    text("""
                        SELECT agent_type, name, status, tasks_completed_today, 
                               total_tasks_completed, last_active_at
                        FROM ai_agents
                        ORDER BY agent_type
                    """)
                )
                agents = agent_result.fetchall()

            agent_names = {v["type"].value: v["name"] for v in AGENT_INFO.values()}

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
当前时间：{datetime.now(CHINA_TZ).strftime('%Y-%m-%d %H:%M')}

团队概况：共{len(agents) if agents else 0}个AI员工，{online_count}个在线，{offline_count}个离线。

各员工状态：
{chr(10).join(raw_lines) if raw_lines else '暂无员工数据'}

今日任务统计：
{chr(10).join(task_lines) if task_lines else '今天暂时没有任务记录'}"""

            smart_response = await self.chat(
                context,
                "你是郑总的私人助理，在微信上聊天。用口语，短句，挑重点说团队情况就好，不要逐个列举。不要用markdown、标签、分隔线。"
            )
            return self._ok(smart_response)

        except Exception as e:
            logger.error(f"[TeamSkill] 查询团队状态失败: {e}")
            return self._err(f"查询团队状态时出错：{str(e)}")

    # ==================== 任务分配 ====================
    
    # 可以直接执行的任务类型映射（混合方案优化）
    DIRECT_EXECUTE_MAPPING = {
        "lead_hunter": {
            "keywords": ["搜索线索", "找线索", "搜线索", "获客", "找客户", "发现话题"],
            "direct_tool": "search_leads",
            "tool_args_builder": lambda desc: {"max_results": 10}
        },
        "copywriter": {
            "keywords": ["写文案", "写脚本", "写广告", "写邮件", "朋友圈文案", "营销文案"],
            "direct_tool": "write_copy",
            "tool_args_builder": lambda desc: {"topic": desc, "copy_type": "general"}
        },
        "video_creator": {
            "keywords": ["生成视频", "做视频", "创建视频", "视频制作"],
            "direct_tool": "create_video",
            "tool_args_builder": lambda desc: {"title": desc, "mode": "quick"}
        },
        "analyst": {
            "keywords": ["分析客户", "客户分析", "意向分析", "客户画像"],
            "direct_tool": "analyze_customer",
            "tool_args_builder": lambda desc: {"conversation": desc}
        },
        "follow": {
            "keywords": ["跟进", "发跟进", "生成跟进", "写跟进邮件"],
            "direct_tool": "generate_followup",
            "tool_args_builder": lambda desc: {"context": desc, "followup_type": "email"}
        }
    }

    async def _handle_agent_dispatch(self, message: str, intent: Dict, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """向指定AI员工分配任务
        
        混合方案优化：
        1. 优先检查是否可以直接执行（不走异步任务队列）
        2. 对于复杂或长时间任务，走异步派发流程
        """
        await self.log_step("think", "分析任务分配", "判断是否可直接执行或需要派发")

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
{{"target_agent": "agent_type", "task_description": "具体任务内容", "priority": "medium", "project": "所属项目名称（如有，如'独立站项目'、'欧洲物流方案'，没有则为空字符串）", "can_direct_execute": true/false}}

can_direct_execute判断标准：
- 简单的搜索线索、写文案、生成短视频 = true
- 复杂的长视频、批量任务、需要多步骤配合 = false

只返回JSON。
"""
        try:
            response = await self.think([{"role": "user", "content": dispatch_prompt}], temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)

            if not json_match:
                return self._err("请明确告诉我要让哪个AI员工做什么任务。")

            dispatch_data = json.loads(json_match.group())
            target_agent_key = dispatch_data.get("target_agent", "")
            task_desc = dispatch_data.get("task_description", message)
            priority = dispatch_data.get("priority", "medium")
            project_name = dispatch_data.get("project", "")
            can_direct = dispatch_data.get("can_direct_execute", False)
            
            # ===== 混合方案优化：尝试直接执行 =====
            if can_direct and target_agent_key in self.DIRECT_EXECUTE_MAPPING:
                direct_config = self.DIRECT_EXECUTE_MAPPING[target_agent_key]
                
                # 检查任务描述是否匹配直接执行关键词
                if any(kw in message.lower() or kw in task_desc.lower() for kw in direct_config["keywords"]):
                    await self.log_step("action", f"直接执行任务", f"使用Maria直接能力执行: {target_agent_key}")
                    
                    try:
                        from app.skills.maria_direct import MariaDirectSkill
                        direct_skill = MariaDirectSkill()
                        direct_skill.agent = self.agent  # 传递agent引用
                        
                        tool_name = direct_config["direct_tool"]
                        tool_args = direct_config["tool_args_builder"](task_desc)
                        
                        result = await direct_skill.handle(
                            tool_name=tool_name,
                            args=tool_args,
                            message=task_desc,
                            user_id=user_id
                        )
                        
                        if result.get("status") == "success":
                            agent_info = AGENT_INFO.get(target_agent_key)
                            agent_name = agent_info["name"] if agent_info else target_agent_key
                            
                            # 构建友好的返回消息
                            return self._ok(
                                f"已直接完成{agent_name}的任务！\n\n{result.get('message', '执行成功')}",
                                direct_execute=True,
                                result=result
                            )
                    except Exception as direct_err:
                        logger.warning(f"[TeamSkill] 直接执行失败，回退到异步派发: {direct_err}")
                        # 继续走异步派发流程

            agent_info = AGENT_INFO.get(target_agent_key)
            if not agent_info:
                return self._err(f"未找到AI员工: {target_agent_key}，请确认员工名称。")

            agent_name = agent_info["name"]
            agent_type = agent_info["type"]

            target_agent = AgentRegistry.get(agent_type)
            if not target_agent:
                return self._err(f"{agent_name}当前未上线，无法分配任务。")

            await self.log_step("think", f"分配任务给{agent_name}", task_desc[:100])

            task_id = str(uuid.uuid4())
            now_iso = datetime.now(CHINA_TZ).isoformat()
            
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

            # 写入 Notion 任务看板
            try:
                from app.skills.notion import get_notion_skill
                notion_skill = await get_notion_skill()
                notion_row_data = {
                    "title": task_desc[:100],
                    "agent_type": target_agent_key,
                    "status": "等待中",
                    "priority": priority,
                    "created_at": now_iso,
                }
                if project_name:
                    notion_row_data["project"] = project_name
                notion_page_id = await notion_skill.upsert_task_row(task_id, notion_row_data)
                # 存回 notion_page_id
                if notion_page_id:
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            text("UPDATE ai_tasks SET notion_page_id = :npid WHERE id = :tid"),
                            {"npid": notion_page_id, "tid": task_id}
                        )
                        await db.commit()
            except Exception as e:
                logger.warning(f"[TeamSkill] Notion看板写入失败（不影响任务分配）: {e}")

            return self._ok(
                f"任务已分配给{agent_name}：{task_desc[:80]}",
                task_id=task_id,
                target_agent=target_agent_key,
                async_execute=True,
            )

        except Exception as e:
            logger.error(f"[TeamSkill] 任务分配失败: {e}")
            return self._err(f"任务分配时出错：{str(e)}")

    # ==================== 升级Agent ====================

    async def _handle_agent_upgrade(self, message: str, intent: Dict, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """升级AI员工能力（修改Prompt）"""
        await self.log_step("think", "分析升级需求", "识别目标AI员工和优化方向")

        target_agent_key = None
        target_agent_name = None

        for key, info in AGENT_INFO.items():
            if info["name"] in message:
                target_agent_key = key
                target_agent_name = info["name"]
                break

        if not target_agent_key:
            try:
                identify_prompt = f"""从以下消息中识别要升级的AI员工名称：
消息：{message}

可选AI员工：小调、小影、小文、小销、小跟、小析、小猎、小欧间谍
返回JSON：{{"agent_name": "名称", "agent_key": "英文key"}}
只返回JSON。"""
                resp = await self.think([{"role": "user", "content": identify_prompt}], temperature=0.3)
                match = re.search(r'\{.*\}', resp, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    target_agent_key = data.get("agent_key")
                    target_agent_name = data.get("agent_name")
            except Exception:
                pass

        if not target_agent_key or target_agent_key not in AGENT_INFO:
            return self._err("请告诉我要升级哪个AI员工？\n\n可选：小调、小影、小文、小销、小跟、小析、小猎、小欧间谍")

        agent = AgentRegistry.get(AGENT_INFO[target_agent_key]["type"])
        if not agent:
            return self._err(f"{target_agent_name}当前未上线。")

        current_prompt = agent.system_prompt

        upgrade_prompt = AGENT_UPGRADE_PROMPT.format(
            agent_name=target_agent_name,
            agent_type=target_agent_key,
            current_prompt=current_prompt[:1000],
            requirement=message
        )

        await self.log_step("think", f"正在分析{target_agent_name}的优化方案", "生成Prompt优化建议")

        try:
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

            suggestion = await self.think([{"role": "user", "content": upgrade_prompt}], temperature=0.7)
            if len(suggestion) > 800:
                suggestion = suggestion[:800] + "..."

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

            return self._ok(
                f"我看了一下{target_agent_name}的现状，给你出个升级方案：\n\n{suggestion}\n\n你看行不行？说「通过」我就改。"
            )

        except Exception as e:
            logger.error(f"[TeamSkill] 生成升级方案失败: {e}")
            return self._ok(f"方案生成的时候出了点问题：{str(e)[:100]}")

    # ==================== 读取代码 ====================

    async def _handle_agent_code_read(self, message: str, intent: Dict, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """查看AI员工代码逻辑"""
        await self.log_step("search", "查找AI员工代码", "准备读取代码文件")

        target_agent_key = None
        target_agent_name = None

        for key, info in AGENT_INFO.items():
            if info["name"] in message:
                target_agent_key = key
                target_agent_name = info["name"]
                break

        if not target_agent_key:
            return self._err("请告诉我要查看哪个AI员工的代码？\n\n可选：小调、小影、小文、小销、小跟、小析、小猎、小欧间谍")

        agent = AgentRegistry.get(AGENT_INFO[target_agent_key]["type"])
        if not agent:
            return self._err(f"{target_agent_name}当前未上线。")

        prompt_preview = agent.system_prompt[:800] if agent.system_prompt else "无Prompt"

        response_text = f"{target_agent_name}代码概览\n\n系统提示词预览：\n{prompt_preview}"
        if len(agent.system_prompt or '') > 800:
            response_text += "\n...(Prompt较长已截取)"

        response_text += f"\n\n基本信息：\n• 类型: {target_agent_key}\n• 物流专家模式: {'开启' if agent.enable_logistics_expertise else '关闭'}\n• 实时直播: {'开启' if agent.enable_live_broadcast else '关闭'}"

        return self._ok(response_text)

    # ==================== 系统状态 ====================

    async def _handle_system_status(self, message: str, intent: Dict, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """检查系统健康状态"""
        await self.log_step("search", "检查系统状态", "全面健康检查中")

        try:
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
                    "系统健康状态",
                    f"整体: {status_emoji} {overall_status.upper()}",
                    f"检查时间: {datetime.now(CHINA_TZ).strftime('%H:%M')}",
                ]

                issues = health.get("issues", [])
                if issues:
                    lines.append("\n⚠️ 问题:")
                    for issue in issues[:5]:
                        lines.append(f"  • {issue}")
                else:
                    lines.append("\n✅ 所有系统运行正常")

                return self._ok("\n".join(lines))

            return self._ok("系统监控服务暂不可用")

        except Exception as e:
            logger.error(f"[TeamSkill] 系统检查失败: {e}")
            return self._err(f"系统检查时出错：{str(e)}")

    # ==================== AI日报 ====================

    async def _handle_ai_daily_report(self, message: str, intent: Dict, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """生成AI团队日报"""
        await self.log_step("think", "生成AI团队日报", "汇总所有AI员工工作数据")

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

                return self._ok(readable_report)

            return self._ok("报告服务暂不可用")

        except Exception as e:
            logger.error(f"[TeamSkill] 生成日报失败: {e}")
            return self._err(f"生成日报时出错：{str(e)}")

    # ==================== 任务状态 ====================

    async def _handle_task_status(self, message: str, intent: Dict, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """查询任务状态"""
        await self.log_step("search", "查询任务状态", "获取最近任务记录")

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
                return self._ok(smart_response)

            agent_names = {v["type"].value: v["name"] for v in AGENT_INFO.values()}

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

                if created_at:
                    if created_at.tzinfo is None:
                        created_at = pytz.UTC.localize(created_at)
                    china_time = created_at.astimezone(CHINA_TZ)
                    time_str = china_time.strftime('%m-%d %H:%M')
                else:
                    time_str = ""

                task_lines.append(f"{name}的任务「{desc}」- {status_text}，时间{time_str}")

            context = f"""用户问：{message}
最近5条任务记录：
{chr(10).join(task_lines)}"""

            smart_response = await self.chat(
                context,
                "你是郑总的私人助理，在微信上聊天。用口语简要说任务情况，不要用markdown、标签、分隔线。"
            )
            return self._ok(smart_response)

        except Exception as e:
            logger.error(f"[TeamSkill] 查询任务状态失败: {e}")
            return self._err(f"查询任务状态时出错：{str(e)}")


# 注册
SkillRegistry.register(TeamManagementSkill())
