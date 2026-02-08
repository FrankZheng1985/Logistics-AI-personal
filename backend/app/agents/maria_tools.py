"""
Maria 的工具定义（Function Calling / Tool Use）

定义所有 Maria 可以调用的工具 schema 和对应的执行函数。
ReAct 循环中，LLM 通过 tool_calls 触发具体工作。
"""
import json
from typing import Dict, Any, List, Callable, Awaitable
from loguru import logger


# ============================================================
# 1. OpenAI 格式的工具 Schema 定义
# ============================================================

MARIA_TOOLS: List[Dict[str, Any]] = [
    # ── 1. 团队管理 ──
    {
        "type": "function",
        "function": {
            "name": "check_agent_status",
            "description": "查看AI团队（9个AI员工）的工作状态、最近任务完成情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "可选，指定查看某个员工，如'小猎'、'小文'。不传则查看全部"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dispatch_agent_task",
            "description": "给AI员工分配具体工作任务，如让小猎找线索、让小文写文章、让小欧监控海关",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "目标员工名称，如'小猎'、'小文'、'小欧间谍'"
                    },
                    "task_description": {
                        "type": "string",
                        "description": "任务描述，详细说明要做什么"
                    }
                },
                "required": ["agent_name", "task_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "upgrade_agent",
            "description": "升级AI员工的能力（修改Prompt），需要先出方案等老板审批",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "要升级的员工名称"
                    },
                    "upgrade_direction": {
                        "type": "string",
                        "description": "升级方向，比如'提高线索识别准确率'、'增加情感分析能力'"
                    }
                },
                "required": ["agent_name", "upgrade_direction"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_agent_code",
            "description": "查看某个AI员工的代码逻辑或当前Prompt",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "要查看的员工名称"
                    }
                },
                "required": ["agent_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_agent_code",
            "description": "修改AI员工的代码或Prompt，需要先出方案等老板审批",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "要修改的员工名称"
                    },
                    "modification": {
                        "type": "string",
                        "description": "具体要修改什么内容"
                    }
                },
                "required": ["agent_name", "modification"]
            }
        }
    },

    # ── 2. 系统管理 ──
    {
        "type": "function",
        "function": {
            "name": "check_system_status",
            "description": "检查整个系统的健康状态：API、数据库、服务是否正常",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_ai_report",
            "description": "生成AI团队的工作日报，包含各员工任务完成情况和统计",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_task_status",
            "description": "查询任务执行状态，可以查最近的任务或指定员工的任务",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "可选，查某个员工的任务"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "可选，查指定任务ID"
                    }
                },
                "required": []
            }
        }
    },

    # ── 3. 日程管理 ──
    {
        "type": "function",
        "function": {
            "name": "add_schedule",
            "description": "帮老板添加日程/提醒。支持设置时间、提醒等",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "日程标题"
                    },
                    "date": {
                        "type": "string",
                        "description": "日期，格式YYYY-MM-DD"
                    },
                    "time": {
                        "type": "string",
                        "description": "时间，格式HH:MM，可选"
                    },
                    "remind_before": {
                        "type": "integer",
                        "description": "提前多少分钟提醒，可选"
                    }
                },
                "required": ["title", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_schedule",
            "description": "查询日程安排。可以查今天、明天、本周、指定日期",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_range": {
                        "type": "string",
                        "description": "查询范围：today/tomorrow/this_week/next_week/指定日期YYYY-MM-DD"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_schedule",
            "description": "修改或取消已有的日程",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "日程ID，可选（如果知道的话）"
                    },
                    "title_keyword": {
                        "type": "string",
                        "description": "日程标题关键词，用于查找要修改的日程"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["update", "cancel"],
                        "description": "操作：update=修改 / cancel=取消"
                    },
                    "new_title": {
                        "type": "string",
                        "description": "新标题（修改时用）"
                    },
                    "new_date": {
                        "type": "string",
                        "description": "新日期（修改时用）"
                    },
                    "new_time": {
                        "type": "string",
                        "description": "新时间（修改时用）"
                    }
                },
                "required": ["action"]
            }
        }
    },

    # ── 4. 待办管理 ──
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description": "添加待办事项",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "待办内容"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "优先级"
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_todo",
            "description": "查询待办事项列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "completed", "all"],
                        "description": "筛选状态"
                    }
                },
                "required": []
            }
        }
    },

    # ── 5. 文档生成 ──
    {
        "type": "function",
        "function": {
            "name": "generate_ppt",
            "description": "生成PPT演示文稿。根据老板的主题需求生成专业PPT",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "PPT主题"
                    },
                    "requirements": {
                        "type": "string",
                        "description": "额外要求（风格、页数、重点内容等）"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_word",
            "description": "生成Word文档（计划书/方案/报告/合同等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_type": {
                        "type": "string",
                        "description": "文档类型：计划书/方案/报告/合同/分析报告"
                    },
                    "topic": {
                        "type": "string",
                        "description": "文档主题"
                    },
                    "requirements": {
                        "type": "string",
                        "description": "额外要求"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_code",
            "description": "帮老板写代码、改Bug、做技术方案",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "编程语言：Python/JavaScript/SQL 等"
                    },
                    "task": {
                        "type": "string",
                        "description": "具体代码需求描述"
                    }
                },
                "required": ["task"]
            }
        }
    },

    # ── 6. 邮件和汇报 ──
    {
        "type": "function",
        "function": {
            "name": "read_emails",
            "description": "深度读取和分析邮件，分类、摘要、给出处理建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "读取最近几封邮件，默认10"
                    },
                    "filter_keyword": {
                        "type": "string",
                        "description": "可选，过滤关键词"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_work_summary",
            "description": "生成工作总结（日报/周报/月报），汇总今天或本周的工作成果",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "汇总周期：daily=日报, weekly=周报, monthly=月报"
                    }
                },
                "required": ["period"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_daily_report",
            "description": "获取每日简报（早报/晚报），包括行业新闻、汇率、天气等",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    # ── 7. 日历文件 ──
    {
        "type": "function",
        "function": {
            "name": "generate_ical",
            "description": "生成iCal日历文件(.ics)，用户可以直接导入苹果日历/Google Calendar/Outlook。支持单个或多个日程事件，支持重复日程",
            "parameters": {
                "type": "object",
                "properties": {
                    "events": {
                        "type": "array",
                        "description": "日程事件列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "事件标题"},
                                "start_date": {"type": "string", "description": "开始日期时间 YYYY-MM-DD HH:MM"},
                                "end_date": {"type": "string", "description": "结束日期时间 YYYY-MM-DD HH:MM（可选）"},
                                "location": {"type": "string", "description": "地点（可选）"},
                                "description": {"type": "string", "description": "备注（可选）"},
                                "is_recurring": {"type": "boolean", "description": "是否重复"},
                                "recurring_pattern": {"type": "string", "description": "重复规则如'每周一'、'每天'、'每月'"}
                            },
                            "required": ["title", "start_date"]
                        }
                    }
                },
                "required": ["events"]
            }
        }
    },

    # ── 8. 身份管理 ──
    {
        "type": "function",
        "function": {
            "name": "change_my_name",
            "description": "老板要给我改名字，我直接改",
            "parameters": {
                "type": "object",
                "properties": {
                    "new_name": {
                        "type": "string",
                        "description": "新名字"
                    }
                },
                "required": ["new_name"]
            }
        }
    },
]


# ============================================================
# 2. 工具执行器 — 把 tool_call 路由到对应的 handler
# ============================================================

class MariaToolExecutor:
    """
    工具执行器：接收 tool_call，解析参数，调用 agent 上对应的 handler。
    与 ClauwdbotAgent（assistant_agent.py）的实例绑定。
    """

    def __init__(self, agent):
        """
        Args:
            agent: ClauwdbotAgent 实例，拥有所有 _handle_* 方法
        """
        self.agent = agent

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        执行一个工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数 dict
            user_id: 用户ID
        
        Returns:
            工具执行结果 dict
        """
        logger.info(f"[Maria Tool] 执行工具: {tool_name}, 参数: {arguments}")

        # 构造兼容旧 handler 的 intent dict
        intent = {"type": tool_name, "params": arguments}
        
        # 把参数合并到 message 字符串中（某些 handler 需要原始消息）
        message = arguments.get("task_description") or arguments.get("topic") or arguments.get("task") or arguments.get("content") or arguments.get("modification") or arguments.get("upgrade_direction") or ""

        try:
            handler = self._get_handler(tool_name)
            if handler:
                result = await handler(message=message, intent=intent, user_id=user_id, args=arguments)
                return result
            else:
                return {"status": "error", "message": f"未知工具: {tool_name}"}
        except Exception as e:
            logger.error(f"[Maria Tool] 工具 {tool_name} 执行失败: {e}")
            return {"status": "error", "message": f"执行失败: {str(e)}"}

    def _get_handler(self, tool_name: str):
        """根据工具名获取对应的处理函数"""
        handler_map = {
            "check_agent_status": self._tool_check_agent_status,
            "dispatch_agent_task": self._tool_dispatch_agent_task,
            "upgrade_agent": self._tool_upgrade_agent,
            "read_agent_code": self._tool_read_agent_code,
            "modify_agent_code": self._tool_modify_agent_code,
            "check_system_status": self._tool_check_system_status,
            "generate_ai_report": self._tool_generate_ai_report,
            "check_task_status": self._tool_check_task_status,
            "add_schedule": self._tool_add_schedule,
            "query_schedule": self._tool_query_schedule,
            "update_schedule": self._tool_update_schedule,
            "add_todo": self._tool_add_todo,
            "query_todo": self._tool_query_todo,
            "generate_ppt": self._tool_generate_ppt,
            "generate_word": self._tool_generate_word,
            "generate_code": self._tool_generate_code,
            "read_emails": self._tool_read_emails,
            "generate_work_summary": self._tool_generate_work_summary,
            "query_daily_report": self._tool_query_daily_report,
            "change_my_name": self._tool_change_name,
            "generate_ical": self._tool_generate_ical,
        }
        return handler_map.get(tool_name)

    # ────── 工具适配层：把新参数格式适配到旧 handler ──────

    async def _tool_check_agent_status(self, message, intent, user_id, args):
        return await self.agent._handle_agent_status(message, intent, user_id)

    async def _tool_dispatch_agent_task(self, message, intent, user_id, args):
        # 将 agent_name 放入 intent 让旧 handler 能找到目标
        intent["target_agent"] = args.get("agent_name", "")
        intent["task"] = args.get("task_description", "")
        return await self.agent._handle_agent_dispatch(
            f"让{args.get('agent_name', '')} {args.get('task_description', '')}", 
            intent, user_id
        )

    async def _tool_upgrade_agent(self, message, intent, user_id, args):
        intent["target_agent"] = args.get("agent_name", "")
        return await self.agent._handle_agent_upgrade(
            f"升级{args.get('agent_name', '')}的{args.get('upgrade_direction', '')}", 
            intent, user_id
        )

    async def _tool_read_agent_code(self, message, intent, user_id, args):
        intent["target_agent"] = args.get("agent_name", "")
        return await self.agent._handle_agent_code_read(
            f"查看{args.get('agent_name', '')}的代码", intent, user_id
        )

    async def _tool_modify_agent_code(self, message, intent, user_id, args):
        intent["target_agent"] = args.get("agent_name", "")
        return await self.agent._handle_agent_code_modify(
            f"修改{args.get('agent_name', '')} {args.get('modification', '')}", 
            intent, user_id
        )

    async def _tool_check_system_status(self, message, intent, user_id, args):
        return await self.agent._handle_system_status(message, intent, user_id)

    async def _tool_generate_ai_report(self, message, intent, user_id, args):
        return await self.agent._handle_ai_daily_report(message, intent, user_id)

    async def _tool_check_task_status(self, message, intent, user_id, args):
        if args.get("agent_name"):
            intent["target_agent"] = args["agent_name"]
        return await self.agent._handle_task_status(message, intent, user_id)

    async def _tool_add_schedule(self, message, intent, user_id, args):
        # 构造一个自然语言消息，让旧 handler 用 LLM 解析
        parts = [args.get("title", "")]
        if args.get("date"):
            parts.append(args["date"])
        if args.get("time"):
            parts.append(args["time"])
        msg = " ".join(parts)
        return await self.agent._handle_schedule_add(msg, intent, user_id)

    async def _tool_query_schedule(self, message, intent, user_id, args):
        date_range = args.get("date_range", "today")
        return await self.agent._handle_schedule_query(f"查看{date_range}的日程", intent, user_id)

    async def _tool_update_schedule(self, message, intent, user_id, args):
        return await self.agent._handle_schedule_update(
            json.dumps(args, ensure_ascii=False), intent, user_id
        )

    async def _tool_add_todo(self, message, intent, user_id, args):
        return await self.agent._handle_todo_add(
            args.get("content", ""), intent, user_id
        )

    async def _tool_query_todo(self, message, intent, user_id, args):
        return await self.agent._handle_todo_query(message, intent, user_id)

    async def _tool_generate_ppt(self, message, intent, user_id, args):
        topic = args.get("topic", "")
        req = args.get("requirements", "")
        return await self.agent._handle_generate_ppt(
            f"{topic} {req}".strip(), intent, user_id
        )

    async def _tool_generate_word(self, message, intent, user_id, args):
        topic = args.get("topic", "")
        doc_type = args.get("doc_type", "报告")
        req = args.get("requirements", "")
        return await self.agent._handle_generate_word(
            f"帮我写一个{doc_type}，主题：{topic} {req}".strip(), intent, user_id
        )

    async def _tool_generate_code(self, message, intent, user_id, args):
        lang = args.get("language", "Python")
        task = args.get("task", "")
        return await self.agent._handle_generate_code(
            f"用{lang}写 {task}", intent, user_id
        )

    async def _tool_read_emails(self, message, intent, user_id, args):
        return await self.agent._handle_email_deep_read(message, intent, user_id)

    async def _tool_generate_work_summary(self, message, intent, user_id, args):
        period = args.get("period", "daily")
        if period == "weekly":
            return await self.agent._handle_weekly_summary(message, intent, user_id)
        else:
            return await self.agent._handle_daily_summary(message, intent, user_id)

    async def _tool_query_daily_report(self, message, intent, user_id, args):
        return await self.agent._handle_daily_report(message, intent, user_id)

    async def _tool_change_name(self, message, intent, user_id, args):
        new_name = args.get("new_name", "")
        return await self.agent._handle_change_name(
            f"以后叫你{new_name}", intent, user_id
        )

    async def _tool_generate_ical(self, message, intent, user_id, args):
        """生成iCal日历文件"""
        from datetime import datetime
        
        events_raw = args.get("events", [])
        if not events_raw:
            return {"status": "error", "message": "没有提供日程事件"}
        
        events = []
        for ev in events_raw:
            start_str = ev.get("start_date", "")
            start_dt = None
            end_dt = None
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            except Exception:
                try:
                    start_dt = datetime.fromisoformat(start_str)
                except Exception:
                    continue
            
            end_str = ev.get("end_date")
            if end_str:
                try:
                    end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
                except Exception:
                    pass
            
            events.append({
                "title": ev.get("title", "日程"),
                "start_time": start_dt,
                "end_time": end_dt,
                "location": ev.get("location"),
                "description": ev.get("description"),
                "is_recurring": ev.get("is_recurring", False),
                "recurring_pattern": ev.get("recurring_pattern"),
            })
        
        if not events:
            return {"status": "error", "message": "日程时间解析失败"}
        
        filepath = self.agent._generate_ical_file(
            title=events[0]["title"],
            start_time=events[0]["start_time"],
            end_time=events[0].get("end_time"),
            location=events[0].get("location"),
            description=events[0].get("description"),
            is_recurring=events[0].get("is_recurring", False),
            recurring_pattern=events[0].get("recurring_pattern"),
            events=events if len(events) > 1 else None,
        )
        
        return {
            "status": "success",
            "message": f"已生成包含{len(events)}个事件的iCal文件",
            "filepath": filepath,
            "event_count": len(events),
        }
