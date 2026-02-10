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
            "name": "analyze_email_attachment",
            "description": "分析邮件中的附件文档（合同/发票/报价单等）。可以搜索特定邮件的附件进行分析，支持Word/PDF/TXT格式",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_keyword": {
                        "type": "string",
                        "description": "搜索关键词，用于找到对应邮件。如'合同'、'铁路运输'、'欧桥'"
                    },
                    "email_id": {
                        "type": "string",
                        "description": "可选，直接指定邮件ID"
                    },
                    "analysis_focus": {
                        "type": "string",
                        "description": "可选，分析重点。如'风险条款'、'价格'、'付款条件'"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ignore_email",
            "description": "将邮件加入忽略列表，以后不再提醒。当老板说'不处理'、'已读'、'过滤'、'不用管'、'跳过'等时调用此工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "要忽略的邮件标识：可以是邮件主题关键词（如'Maria助理'）、发件人邮箱（如'noreply@xxx.com'）、或完整主题"
                    },
                    "reason": {
                        "type": "string",
                        "description": "可选，忽略原因（便于以后查看）"
                    }
                },
                "required": ["identifier"]
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

    # ── 8. 联网搜索 ──
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "在Google上搜索实时信息。可以搜索新闻、公司背景、行业动态、政策法规、物流价格、任何问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，用自然语言描述"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["search", "news"],
                        "description": "搜索类型：search=网页搜索（默认），news=新闻搜索"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认5，最多10"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage",
            "description": "抓取指定网址的内容，可以用来深入阅读某篇文章、查看公司官网、读取网页详情",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要抓取的网页URL"
                    }
                },
                "required": ["url"]
            }
        }
    },

    # ── 9. 苹果日历直写 ──
    {
        "type": "function",
        "function": {
            "name": "add_to_apple_calendar",
            "description": "直接往老板的苹果手机日历里添加日程事件。支持单个或多个事件，支持重复日程。这是真的写入苹果日历，不是生成文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "events": {
                        "type": "array",
                        "description": "要添加的日程事件列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "事件标题"},
                                "start_date": {"type": "string", "description": "开始时间 YYYY-MM-DD HH:MM"},
                                "end_date": {"type": "string", "description": "结束时间 YYYY-MM-DD HH:MM（可选，默认1小时后）"},
                                "location": {"type": "string", "description": "地点（可选）"},
                                "description": {"type": "string", "description": "备注（可选）"},
                                "alarm_minutes": {"type": "integer", "description": "提前多少分钟提醒，默认15"},
                                "is_recurring": {"type": "boolean", "description": "是否重复"},
                                "recurring_pattern": {"type": "string", "description": "重复规则：每天/每周/每周一/每月 等"}
                            },
                            "required": ["title", "start_date"]
                        }
                    }
                },
                "required": ["events"]
            }
        }
    },

    # ── 10. 邮件管理（增强版）──
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "通过老板的邮箱发送邮件。可以指定用哪个邮箱发，如果不指定就用默认邮箱",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "收件人邮箱地址列表"
                    },
                    "subject": {
                        "type": "string",
                        "description": "邮件主题"
                    },
                    "body": {
                        "type": "string",
                        "description": "邮件正文内容"
                    },
                    "account_name": {
                        "type": "string",
                        "description": "可选，用哪个邮箱发（如'iCloud邮箱'、'工作邮箱'），不指定则用默认邮箱"
                    }
                },
                "required": ["to_emails", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sync_emails",
            "description": "同步拉取邮箱里的最新邮件，然后可以查看未读邮件。相当于刷新收件箱",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_name": {
                        "type": "string",
                        "description": "可选，同步哪个邮箱。不指定则同步全部邮箱"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_email_account",
            "description": "管理邮箱账户：添加新邮箱、查看已有邮箱列表、删除邮箱、测试邮箱连接",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "add", "delete", "test"],
                        "description": "操作：list=查看邮箱列表, add=添加新邮箱, delete=删除邮箱, test=测试连接"
                    },
                    "name": {
                        "type": "string",
                        "description": "添加时：邮箱别名（如'工作邮箱'、'个人邮箱'）"
                    },
                    "email_address": {
                        "type": "string",
                        "description": "添加时：邮箱地址"
                    },
                    "password": {
                        "type": "string",
                        "description": "添加时：邮箱密码或授权码"
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["icloud", "gmail", "outlook", "qq", "qq_enterprise", "163", "aliyun", "other"],
                        "description": "添加时：邮箱服务商（自动配置IMAP/SMTP）"
                    },
                    "account_name": {
                        "type": "string",
                        "description": "删除/测试时：要操作的邮箱别名"
                    }
                },
                "required": ["action"]
            }
        }
    },

    # ── 11. 身份管理 ──
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

    # ── 12. Notion 集成 ──
    {
        "type": "function",
        "function": {
            "name": "create_notion_page",
            "description": "在 Notion 中创建一个新页面。用于写方案、项目计划、文档、报告、会议纪要等。Maria 会自动生成排版精美的 Notion 页面",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "页面标题"
                    },
                    "content": {
                        "type": "string",
                        "description": "页面内容（Markdown 格式）。如果不传，Maria 会根据标题自动生成内容"
                    },
                    "page_type": {
                        "type": "string",
                        "enum": ["document", "plan", "report", "meeting", "proposal"],
                        "description": "页面类型：document=文档, plan=项目计划, report=报告, meeting=会议纪要, proposal=提案/方案"
                    },
                    "parent_page_id": {
                        "type": "string",
                        "description": "可选，指定父页面 ID。不传则放在 Maria 工作台根目录下"
                    }
                },
                "required": ["title"]
            }
        }
    },

    # ============================================================
    # 13. Maria 直接执行能力（混合方案 - 不经过任务派发）
    # ============================================================
    
    # ── 13.1 线索搜索（直接调用小猎核心能力）──
    {
        "type": "function",
        "function": {
            "name": "search_leads",
            "description": "【直接执行】立即搜索互联网上的潜在客户线索。Maria直接执行，不派发给其他员工，结果实时返回",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索关键词列表，如['欧洲物流', '德国FBA']。不传则使用系统默认关键词"
                    },
                    "platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "搜索平台，可选: google, weibo, zhihu, xiaohongshu, tieba。不传则智能选择"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数，默认10"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discover_topics",
            "description": "【直接执行】发现热门话题，用于内容引流。搜索知乎、小红书等平台的热门物流相关问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_topics": {
                        "type": "integer",
                        "description": "最大返回话题数，默认5"
                    }
                },
                "required": []
            }
        }
    },
    
    # ── 13.2 文案创作（直接调用小文核心能力）──
    {
        "type": "function",
        "function": {
            "name": "write_copy",
            "description": "【直接执行】立即撰写各类营销文案。Maria直接调用文案能力，结果实时返回",
            "parameters": {
                "type": "object",
                "properties": {
                    "copy_type": {
                        "type": "string",
                        "enum": ["script", "long_script", "moments", "ad", "email", "general"],
                        "description": "文案类型: script=短视频脚本, long_script=长视频脚本, moments=朋友圈, ad=广告, email=邮件, general=通用"
                    },
                    "topic": {
                        "type": "string",
                        "description": "文案主题，如'欧洲FBA头程服务'"
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "目标受众，如'跨境电商卖家'"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "视频时长（秒），仅脚本类型需要"
                    },
                    "language": {
                        "type": "string",
                        "description": "语言，默认中文。支持: zh-CN, en-US, de-DE, fr-FR, es-ES, ja-JP 等"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    
    # ── 13.3 视频生成（直接调用小影核心能力）──
    {
        "type": "function",
        "function": {
            "name": "create_video",
            "description": "【直接执行】立即生成AI视频。Maria直接调用视频生成能力，支持5秒短视频或1.5-5分钟长视频",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "视频标题"
                    },
                    "script": {
                        "type": "string",
                        "description": "视频脚本内容。如果没有，Maria会先生成脚本"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["quick", "movie"],
                        "description": "生成模式: quick=5-10秒快速视频, movie=1.5-5分钟电影级视频"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "目标时长（秒），movie模式下默认120秒"
                    },
                    "language": {
                        "type": "string",
                        "description": "配音语言，默认中文"
                    }
                },
                "required": ["title"]
            }
        }
    },
    
    # ── 13.4 客户分析（直接调用小析核心能力）──
    {
        "type": "function",
        "function": {
            "name": "analyze_customer",
            "description": "【直接执行】分析客户意向和画像。Maria直接分析对话内容，给出意向评分和跟进建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "客户ID（如果已有）"
                    },
                    "conversation": {
                        "type": "string",
                        "description": "与客户的对话内容"
                    },
                    "customer_info": {
                        "type": "object",
                        "description": "已知客户信息，如公司名、联系方式等"
                    }
                },
                "required": ["conversation"]
            }
        }
    },
    
    # ── 13.5 客户跟进（直接调用小跟核心能力）──
    {
        "type": "function",
        "function": {
            "name": "generate_followup",
            "description": "【直接执行】生成客户跟进消息或邮件。Maria根据客户情况直接生成个性化跟进内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "客户ID"
                    },
                    "followup_type": {
                        "type": "string",
                        "enum": ["email", "wechat", "phone_script"],
                        "description": "跟进类型: email=邮件, wechat=微信消息, phone_script=电话话术"
                    },
                    "context": {
                        "type": "string",
                        "description": "跟进背景，如'客户上次询价后未回复'"
                    },
                    "language": {
                        "type": "string",
                        "description": "语言，默认根据客户自动检测"
                    }
                },
                "required": ["context"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_followup_email",
            "description": "【直接执行】直接发送跟进邮件给客户。Maria生成内容后直接发送，一步完成",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_email": {
                        "type": "string",
                        "description": "收件人邮箱"
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "客户名称"
                    },
                    "followup_reason": {
                        "type": "string",
                        "description": "跟进原因，如'报价后3天未回复'"
                    },
                    "previous_context": {
                        "type": "string",
                        "description": "之前的沟通内容摘要"
                    },
                    "language": {
                        "type": "string",
                        "description": "邮件语言"
                    }
                },
                "required": ["to_email", "followup_reason"]
            }
        }
    },
    
    # ── 13.6 一键工作流（组合能力）──
    {
        "type": "function",
        "function": {
            "name": "lead_to_video_workflow",
            "description": "【一键工作流】从线索到视频的完整流程：搜索线索→分析高意向→生成针对性文案→制作视频",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "主题方向，如'欧洲FBA'"
                    },
                    "video_duration": {
                        "type": "integer",
                        "description": "视频时长（秒），默认60"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_to_notion_page",
            "description": "往已有的 Notion 页面追加内容。比如追加日报、补充方案细节、添加会议记录等",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "目标页面 ID（如果知道的话）"
                    },
                    "title_keyword": {
                        "type": "string",
                        "description": "页面标题关键词（如果不知道 page_id，通过标题搜索定位）"
                    },
                    "content": {
                        "type": "string",
                        "description": "要追加的内容（Markdown 格式）"
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_notion",
            "description": "搜索 Notion 工作空间中的内容。可以找方案、文档、笔记、项目等",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["page", "database"],
                        "description": "搜索类型：page=搜索页面, database=搜索数据库"
                    }
                },
                "required": ["query"]
            }
        }
    },
]


# ============================================================
# 2. 工具执行器 — 把 tool_call 路由到对应的 handler
# ============================================================

class MariaToolExecutor:
    """
    工具执行器 - 将 LLM 的 tool_calls 路由到 Skill 模块
    
    新架构（Phase 1 重构）：
    1. LLM 返回 tool_calls (含 function name + arguments)
    2. MariaToolExecutor 通过 SkillRegistry 查找对应 Skill
    3. 委托给 Skill.handle() 执行
    4. 返回结果放回对话上下文，让 LLM 决定下一步
    """

    def __init__(self, agent):
        """
        Args:
            agent: ClauwdbotAgent 实例
        """
        self.agent = agent
        self._skill_map = None  # 懒加载

    def _get_skill_map(self) -> Dict[str, Any]:
        """获取 tool_name -> skill 的映射（懒加载 + 绑定agent）"""
        if self._skill_map is None:
            from app.skills.base import SkillRegistry
            self._ensure_skills_loaded()
            self._skill_map = SkillRegistry.get_tool_mapping()
            # 绑定 agent 引用到所有 skill
            for skill in SkillRegistry.get_all().values():
                if skill.agent is None:
                    skill.agent = self.agent
        return self._skill_map

    @staticmethod
    def _ensure_skills_loaded():
        """确保所有skill模块已被导入（触发注册）"""
        try:
            import app.skills.team_management
            import app.skills.schedule
            import app.skills.email
            import app.skills.search
            import app.skills.document
            import app.skills.self_config
            import app.skills.notion
            # 混合方案新增：Maria直接执行技能
            import app.skills.maria_direct
        except ImportError as e:
            logger.warning(f"[MariaToolExecutor] 部分Skill模块加载失败: {e}")

    @staticmethod
    def _mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏处理（用于日志记录）"""
        masked = data.copy()
        sensitive_keys = {"password", "api_key", "secret", "token", "credential", "auth"}
        
        for key in masked:
            if any(s in key.lower() for s in sensitive_keys):
                masked[key] = "******"
        return masked

    async def execute(self, tool_name: str, arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        执行一个工具调用 - 路由到对应的Skill模块
        """
        # 日志脱敏
        safe_args = self._mask_sensitive_data(arguments)
        logger.info(f"[Maria Tool] 执行工具: {tool_name}, 参数: {safe_args}")

        # 构造自然语言 message（用于Skill内部LLM解析）
        message = self._build_message(tool_name, arguments)

        try:
            skill_map = self._get_skill_map()
            skill = skill_map.get(tool_name)
            
            if skill:
                result = await skill.handle(
                    tool_name=tool_name,
                    args=arguments,
                    message=message,
                    user_id=user_id,
                )
                return result
            else:
                logger.warning(f"[Maria Tool] 未找到工具 {tool_name} 对应的Skill")
                return {"status": "error", "message": f"未知工具: {tool_name}，这个功能我还不支持"}
        except Exception as e:
            logger.error(f"[Maria Tool] 工具 {tool_name} 执行失败: {e}", exc_info=True)
            # 返回详细错误信息，让 LLM 能据此给老板清楚的回复
            return {
                "status": "error",
                "message": f"执行 {tool_name} 时出错：{str(e)[:300]}",
                "tool_name": tool_name,
                "error_type": type(e).__name__,
            }

    @staticmethod
    def _build_message(tool_name: str, arguments: Dict[str, Any]) -> str:
        """根据工具名和参数构造自然语言消息（供Skill内部LLM解析用）"""
        if tool_name == "dispatch_agent_task":
            return f"让{arguments.get('agent_name', '')} {arguments.get('task_description', '')}"
        elif tool_name == "upgrade_agent":
            return f"升级{arguments.get('agent_name', '')}的{arguments.get('upgrade_direction', '')}"
        elif tool_name == "read_agent_code":
            return f"查看{arguments.get('agent_name', '')}的代码"
        elif tool_name == "modify_agent_code":
            return f"修改{arguments.get('agent_name', '')} {arguments.get('modification', '')}"
        elif tool_name == "add_schedule":
            parts = [arguments.get("title", "")]
            if arguments.get("date"):
                parts.append(arguments["date"])
            if arguments.get("time"):
                parts.append(arguments["time"])
            return " ".join(parts)
        elif tool_name == "query_schedule":
            return f"查看{arguments.get('date_range', 'today')}的日程"
        elif tool_name == "update_schedule":
            return json.dumps(arguments, ensure_ascii=False)
        elif tool_name == "add_todo":
            return arguments.get("content", "")
        elif tool_name == "generate_ppt":
            topic = arguments.get("topic", "")
            req = arguments.get("requirements", "")
            return f"{topic} {req}".strip()
        elif tool_name == "generate_word":
            topic = arguments.get("topic", "")
            doc_type = arguments.get("doc_type", "报告")
            req = arguments.get("requirements", "")
            return f"帮我写一个{doc_type}，主题：{topic} {req}".strip()
        elif tool_name == "generate_code":
            lang = arguments.get("language", "Python")
            task_desc = arguments.get("task", "")
            return f"用{lang}写 {task_desc}"
        elif tool_name == "change_my_name":
            return f"以后叫你{arguments.get('new_name', '')}"
        elif tool_name == "generate_work_summary":
            return f"生成{arguments.get('period', 'daily')}总结"
        elif tool_name == "create_notion_page":
            title = arguments.get("title", "")
            page_type = arguments.get("page_type", "document")
            return f"在Notion创建{page_type}：{title}"
        elif tool_name == "append_to_notion_page":
            keyword = arguments.get("title_keyword", "")
            return f"往Notion页面{keyword}追加内容"
        elif tool_name == "search_notion":
            return f"搜索Notion：{arguments.get('query', '')}"
        else:
            # 通用回退：从常见参数字段中取值
            return (
                arguments.get("task_description")
                or arguments.get("topic")
                or arguments.get("task")
                or arguments.get("content")
                or arguments.get("query")
                or ""
            )

    # 旧的 _get_handler 和适配层已移除
    # 所有工具逻辑现在由 app.skills.* 模块处理
