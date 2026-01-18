"""
小助 - 个人助理AI员工
负责：日程管理、会议纪要、待办事项、多邮箱管理、ERP数据跟踪
主要通过企业微信与老板沟通
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import json
import re
import pytz

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class AssistantAgent(BaseAgent):
    """小助 - 个人助理AI员工
    
    核心能力：
    1. 日程管理 - 自然语言录入、提醒、查询
    2. 会议纪要 - 录音转写、AI总结、提取待办
    3. 待办事项 - 添加、查询、完成
    4. 多邮箱管理 - 统一收件箱、邮件提醒、草拟回复
    5. ERP数据跟踪 - 订单汇报、财务摘要
    6. 每日简报 - 日程+订单+邮件汇总
    """
    
    name = "小助"
    agent_type = AgentType.ASSISTANT
    description = "个人助理 - 日程管理、会议纪要、邮件管理、ERP数据跟踪"
    
    # 中国时区
    CHINA_TZ = pytz.timezone('Asia/Shanghai')
    
    @staticmethod
    def to_china_time(dt):
        """转换为中国时区时间"""
        if dt is None:
            return None
        # 如果没有时区信息，假设是UTC
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        # 转换到中国时区
        return dt.astimezone(AssistantAgent.CHINA_TZ)
    
    # 意图分类
    INTENT_TYPES = {
        "schedule_add": ["记住", "记录", "安排", "添加日程", "提醒我", "帮我记"],
        "schedule_update": ["修改", "改成", "改为", "调整时间", "更改", "变更日程"],  # 修改日程
        "schedule_query": ["今天", "明天", "有什么安排", "有什么会", "日程", "行程"],
        "schedule_cancel": ["取消", "删除日程", "不开了"],
        "todo_add": ["待办", "要做", "记得做", "别忘了"],
        "todo_query": ["待办列表", "还有什么没做", "待办事项"],
        "todo_complete": ["完成了", "做完了", "搞定了"],
        "meeting_record": ["会议纪要", "整理会议", "会议结束"],
        "email_query": ["邮件", "收件箱", "新邮件", "查看邮件"],
        "email_reply": ["回复邮件", "发邮件"],
        "erp_query": ["订单", "今天多少单", "财务", "营收"],
        "report": ["日报", "汇报", "简报", "今日总结"],
        "help": ["帮助", "你能做什么", "功能"]
    }
    
    def _build_system_prompt(self) -> str:
        return """你是小助，一位专业、高效的个人助理AI。你的职责是帮助老板管理日程、会议、待办事项、邮件和了解业务数据。

## 你的性格特点
- 专业、细心、有条理
- 主动提醒重要事项
- 简洁明了，不啰嗦
- 像一位经验丰富的私人秘书

## 你的核心能力
1. **日程管理**：记录日程、提醒安排、查询行程
2. **会议纪要**：整理会议内容、提取待办任务
3. **待办管理**：记录待办、提醒截止日期
4. **邮件管理**：汇总重要邮件、草拟回复
5. **ERP数据**：汇报订单情况、财务摘要

## 回复风格
- 使用简洁的格式，善用列表和符号
- 重要信息用 📅📋📧📊 等符号标注
- 时间格式统一为"X月X日 周X HH:MM"
- 回复控制在300字以内（企业微信限制）

## 理解用户意图
用户可能用自然语言表达，你需要理解并执行：
- "明天下午3点和张总开会" → 添加日程
- "今天有什么安排" → 查询日程
- "帮我记住：下周五交报告" → 添加待办
- "今天订单情况" → 查询ERP数据
"""
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户消息
        
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
        
        # 开始任务会话
        await self.start_task_session("process_message", f"处理用户消息: {message[:50]}...")
        
        try:
            # 1. 如果是语音/文件消息，可能是会议录音
            if message_type in ["voice", "file"] and file_url:
                await self.log_live_step("think", "收到音频文件", "准备进行会议录音转写")
                result = await self._handle_audio_file(file_url, user_id)
                await self.end_task_session("会议录音处理完成")
                return result
            
            # 2. 解析用户意图
            await self.log_live_step("think", "分析用户意图", message[:100])
            intent = await self._parse_intent(message)
            
            # 3. 根据意图处理
            handler_map = {
                "schedule_add": self._handle_schedule_add,
                "schedule_update": self._handle_schedule_update,  # 修改日程
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
            logger.error(f"[小助] 处理消息失败: {e}")
            await self.log_error(str(e))
            await self.end_task_session(error_message=str(e))
            return {
                "success": False,
                "response": "抱歉，处理您的请求时出现了问题，请稍后再试。",
                "error": str(e)
            }
    
    async def _parse_intent(self, message: str) -> Dict[str, Any]:
        """解析用户意图"""
        message_lower = message.lower()
        
        # 先用关键词匹配
        for intent_type, keywords in self.INTENT_TYPES.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return {"type": intent_type, "confidence": 0.8, "keyword": keyword}
        
        # 关键词匹配失败，使用AI分析
        analysis_prompt = f"""分析用户消息的意图，返回JSON格式：

用户消息：{message}

可能的意图类型：
- schedule_add: 添加新日程/安排（没有明确要修改现有的）
- schedule_update: 修改现有日程（明确提到"修改"、"改成"、"调整"等词）
- schedule_query: 查询日程
- schedule_cancel: 取消日程
- todo_add: 添加待办事项
- todo_query: 查询待办
- todo_complete: 完成待办
- meeting_record: 会议纪要相关
- email_query: 查询邮件
- email_reply: 回复/发送邮件
- erp_query: 查询订单/财务数据
- report: 要日报/汇报
- help: 询问功能/帮助
- unknown: 无法识别

【重要】如果用户说"修改"、"改成"、"改为"、"调整"等词，应识别为schedule_update而不是schedule_add！

返回格式：{{"type": "xxx", "confidence": 0.9, "extracted": {{"time": "...", "content": "..."}}}}
只返回JSON，不要其他内容。
"""
        
        try:
            response = await self.think([{"role": "user", "content": analysis_prompt}], temperature=0.3)
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.warning(f"[小助] AI意图分析失败: {e}")
        
        return {"type": "unknown", "confidence": 0.5}
    
    # ==================== 日程管理 ====================
    
    async def _handle_schedule_add(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理添加日程"""
        await self.log_live_step("think", "解析日程信息", "提取时间、事项、地点")
        
        # 计算各星期几的具体日期
        now = datetime.now()
        weekday_dates = {}
        for i in range(7):
            future_date = now + timedelta(days=i)
            weekday_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][future_date.weekday()]
            if weekday_name not in weekday_dates:  # 只取最近的
                weekday_dates[weekday_name] = future_date.strftime('%Y-%m-%d')
        
        weekday_info = "\n".join([f"- {k}: {v}" for k, v in weekday_dates.items()])
        today_weekday = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
        
        # 使用AI提取日程信息
        extract_prompt = f"""从用户消息中提取日程信息，返回JSON格式：

用户消息：{message}
当前时间：{now.strftime('%Y-%m-%d %H:%M')}，今天是{today_weekday}

【重要】接下来7天的日期对照表（必须使用）：
{weekday_info}

用户说"周一"或"每周一"时，请查上表找到下一个周一的具体日期！

返回格式：
{{
    "title": "日程标题",
    "start_time": "YYYY-MM-DD HH:MM",
    "end_time": "YYYY-MM-DD HH:MM"（如果没有则为null）,
    "location": "地点"（如果没有则为null）,
    "description": "备注"（如果没有则为null）,
    "priority": "normal"（low/normal/high/urgent）,
    "is_recurring": false（如果用户说"每周"、"每天"等重复日程，设为true）,
    "recurring_pattern": null（如果is_recurring为true，填写 "daily"/"weekly"/"monthly"）
}}

只返回JSON，不要其他内容。
"""
        
        try:
            response = await self.think([{"role": "user", "content": extract_prompt}], temperature=0.3)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"success": False, "response": "抱歉，我没能理解日程信息，请用更清晰的方式告诉我，比如：'明天下午3点和张总开会'"}
            
            schedule_data = json.loads(json_match.group())
            
            # 解析时间字符串为datetime对象
            start_time_str = schedule_data.get("start_time")
            end_time_str = schedule_data.get("end_time")
            
            start_time_dt = None
            end_time_dt = None
            
            if start_time_str:
                try:
                    start_time_dt = datetime.fromisoformat(start_time_str)
                except:
                    # 尝试其他格式
                    try:
                        start_time_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
                    except:
                        pass
            
            if end_time_str:
                try:
                    end_time_dt = datetime.fromisoformat(end_time_str)
                except:
                    try:
                        end_time_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
                    except:
                        pass
            
            if not start_time_dt:
                return {"success": False, "response": "抱歉，我没能理解日程的时间，请用更清晰的方式告诉我，比如：'明天下午3点开会'"}
            
            # 保存到数据库
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
            
            # 格式化时间显示
            weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][start_time_dt.weekday()]
            time_str = f"{start_time_dt.month}月{start_time_dt.day}日 {weekday} {start_time_dt.strftime('%H:%M')}"
            
            location_str = f" 📍{schedule_data['location']}" if schedule_data.get('location') else ""
            
            # 检查是否为重复日程
            is_recurring = schedule_data.get('is_recurring', False)
            recurring_note = ""
            if is_recurring:
                pattern = schedule_data.get('recurring_pattern', 'weekly')
                pattern_text = {"daily": "每天", "weekly": "每周", "monthly": "每月"}.get(pattern, "定期")
                recurring_note = f"\n\n📝 注：您说的是{pattern_text}重复日程，目前已记录最近一次。后续版本将支持自动重复提醒。"
            
            response_text = f"""✅ 日程已记录！

📅 {schedule_data['title']}
⏰ {time_str}{location_str}{recurring_note}

我会提前提醒你的。"""
            
            await self.log_result("日程添加成功", schedule_data['title'])
            
            return {"success": True, "response": response_text, "schedule_id": str(row[0])}
            
        except Exception as e:
            logger.error(f"[小助] 添加日程失败: {e}")
            return {"success": False, "response": f"添加日程时出错了：{str(e)}"}
    
    async def _handle_schedule_query(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理查询日程"""
        await self.log_live_step("search", "查询日程", "获取相关日程安排")
        
        # 判断查询的是今天还是明天还是其他
        today = datetime.now().date()
        query_date = today
        date_label = "今天"
        
        if "明天" in message or "明日" in message:
            query_date = today + timedelta(days=1)
            date_label = "明天"
        elif "后天" in message:
            query_date = today + timedelta(days=2)
            date_label = "后天"
        elif "本周" in message or "这周" in message:
            # 查询本周
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            return await self._query_schedule_range(start_of_week, end_of_week, "本周")
        
        # 查询指定日期
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT title, start_time, end_time, location, priority, is_completed
                    FROM assistant_schedules
                    WHERE DATE(start_time) = :query_date
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
        
        # 格式化输出
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
        # TODO: 实现取消日程逻辑
        return {"success": True, "response": "请告诉我要取消哪个日程？比如说'取消明天下午的会议'"}
    
    async def _handle_schedule_update(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理修改日程"""
        await self.log_live_step("think", "解析修改请求", "识别要修改的日程和新信息")
        
        # 计算各星期几的具体日期
        now = datetime.now()
        weekday_dates = {}
        for i in range(7):
            future_date = now + timedelta(days=i)
            weekday_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][future_date.weekday()]
            if weekday_name not in weekday_dates:
                weekday_dates[weekday_name] = future_date.strftime('%Y-%m-%d')
        
        weekday_info = "\n".join([f"- {k}: {v}" for k, v in weekday_dates.items()])
        today_weekday = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
        
        # 使用AI分析修改请求
        extract_prompt = f"""用户想要修改日程，请分析：

用户消息：{message}
当前时间：{now.strftime('%Y-%m-%d %H:%M')}，今天是{today_weekday}

接下来7天的日期对照表：
{weekday_info}

请返回JSON格式：
{{
    "search_keyword": "用于搜索现有日程的关键词（如'先锋团队例会'）",
    "new_time": "YYYY-MM-DD HH:MM"（新的时间，如果要修改时间）或 null,
    "new_title": "新标题"（如果要修改标题）或 null,
    "new_location": "新地点"（如果要修改地点）或 null
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
                return {"success": False, "response": "请告诉我您要修改哪个日程？比如'修改先锋团队例会的时间为上午10点'"}
            
            # 繁简体转换映射（常用字）
            simplified_to_traditional = {
                '锋': '鋒', '团': '團', '队': '隊', '会': '會', '时': '時',
                '间': '間', '与': '與', '开': '開', '议': '議', '报': '報',
                '记': '記', '务': '務', '项': '項', '经': '經', '营': '營',
                '销': '銷', '财': '財', '总': '總', '结': '結', '进': '進',
            }
            traditional_to_simplified = {v: k for k, v in simplified_to_traditional.items()}
            
            def to_simplified(text):
                for t, s in traditional_to_simplified.items():
                    text = text.replace(t, s)
                return text
            
            def to_traditional(text):
                for s, t in simplified_to_traditional.items():
                    text = text.replace(s, t)
                return text
            
            # 生成搜索关键词的多个变体
            search_variants = [
                search_keyword,
                to_simplified(search_keyword),
                to_traditional(search_keyword),
            ]
            # 提取核心词（去掉"例会"、"会议"等后缀）
            core_keyword = search_keyword.replace('例会', '').replace('会议', '').replace('會議', '').strip()
            if core_keyword and core_keyword != search_keyword:
                search_variants.extend([core_keyword, to_simplified(core_keyword), to_traditional(core_keyword)])
            
            # 搜索匹配的日程（尝试多个变体）
            schedules = []
            async with AsyncSessionLocal() as db:
                for variant in search_variants:
                    if schedules:
                        break
                    result = await db.execute(
                        text("""
                            SELECT id, title, start_time, location
                            FROM assistant_schedules
                            WHERE title ILIKE :keyword
                            AND is_completed = FALSE
                            ORDER BY start_time ASC
                            LIMIT 5
                        """),
                        {"keyword": f"%{variant}%"}
                    )
                    schedules = result.fetchall()
                
                # 如果还是没找到，获取所有日程供用户选择
                if not schedules:
                    result = await db.execute(
                        text("""
                            SELECT id, title, start_time, location
                            FROM assistant_schedules
                            WHERE is_completed = FALSE
                            ORDER BY start_time ASC
                            LIMIT 10
                        """)
                    )
                    all_schedules = result.fetchall()
                    
                    if all_schedules:
                        # 转换为中国时区并格式化
                        schedule_items = []
                        for s in all_schedules:
                            china_time = self.to_china_time(s[2])
                            schedule_items.append(f"• {s[1]} ({china_time.strftime('%m月%d日 %H:%M')})")
                        schedule_list = "\n".join(schedule_items)
                        return {
                            "success": False, 
                            "response": f"没有找到'{search_keyword}'相关的日程。\n\n📅 当前日程列表：\n{schedule_list}\n\n请告诉我要修改哪个？"
                        }
                    else:
                        return {
                            "success": False, 
                            "response": "当前没有任何日程记录。请先添加日程，比如说'帮我记住明天下午3点开会'"
                        }
            
            # 取最近的一条日程进行修改
            schedule = schedules[0]
            schedule_id = schedule[0]
            old_title = schedule[1]
            old_time = schedule[2]
            
            # 构建更新内容
            updates = []
            params = {"id": schedule_id}
            
            if update_data.get("new_time"):
                try:
                    new_time = datetime.strptime(update_data["new_time"], "%Y-%m-%d %H:%M")
                    updates.append("start_time = :new_time")
                    params["new_time"] = new_time
                except:
                    pass
            
            if update_data.get("new_title"):
                updates.append("title = :new_title")
                params["new_title"] = update_data["new_title"]
            
            if update_data.get("new_location"):
                updates.append("location = :new_location")
                params["new_location"] = update_data["new_location"]
            
            if not updates:
                return {"success": False, "response": "没有检测到需要修改的内容，请说明要修改什么（时间、标题或地点）。"}
            
            updates.append("updated_at = NOW()")
            
            # 执行更新
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(f"UPDATE assistant_schedules SET {', '.join(updates)} WHERE id = :id"),
                    params
                )
                await db.commit()
            
            # 格式化响应
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
            logger.error(f"[小助] 修改日程失败: {e}")
            return {"success": False, "response": f"修改日程时出错了：{str(e)}"}
    
    # ==================== 待办管理 ====================
    
    async def _handle_todo_add(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理添加待办"""
        await self.log_live_step("think", "解析待办信息", "提取内容和截止日期")
        
        # 使用AI提取待办信息
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
            
            # 保存到数据库
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
            
            response_text = f"""✅ 待办已记录！

📋 {todo_data['content']}{due_str}

需要我提醒你吗？"""
            
            return {"success": True, "response": response_text, "todo_id": str(row[0])}
            
        except Exception as e:
            logger.error(f"[小助] 添加待办失败: {e}")
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
                        CASE priority 
                            WHEN 'urgent' THEN 1 
                            WHEN 'high' THEN 2 
                            WHEN 'normal' THEN 3 
                            ELSE 4 
                        END,
                        due_date ASC NULLS LAST,
                        created_at ASC
                    LIMIT 10
                """)
            )
            todos = result.fetchall()
        
        if not todos:
            return {"success": True, "response": "📋 待办列表\n\n暂无待办事项，真棒！🎉"}
        
        lines = ["📋 待办列表", "━" * 18]
        
        for i, t in enumerate(todos, 1):
            priority_icon = {"urgent": "🔴", "high": "🟡"}.get(t[1], "")
            due_str = ""
            if t[2]:
                due_str = f" (截止{t[2].month}/{t[2].day})"
            lines.append(f"{i}. {priority_icon}{t[0]}{due_str}")
        
        lines.append("━" * 18)
        lines.append(f"共{len(todos)}项待办")
        
        return {"success": True, "response": "\n".join(lines)}
    
    async def _handle_todo_complete(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理完成待办"""
        # TODO: 实现完成待办逻辑
        return {"success": True, "response": "请告诉我完成了哪个待办？可以说待办的编号或内容。"}
    
    # ==================== 会议纪要 ====================
    
    async def _handle_audio_file(self, file_url: str, user_id: str) -> Dict[str, Any]:
        """处理音频文件（会议录音）"""
        from app.services.speech_recognition_service import speech_recognition_service
        
        await self.log_live_step("fetch", "下载音频文件", file_url[:50])
        
        # 创建会议记录
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
        
        # 启动异步转写任务
        await self.log_live_step("think", "开始语音转写", "这可能需要几分钟时间")
        
        # 返回确认消息，转写在后台进行
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
            # 获取未读邮件摘要
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
            logger.error(f"[小助] 查询邮件失败: {e}")
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
            # 获取今日订单统计
            today = datetime.now().strftime("%Y-%m-%d")
            orders_data = await erp_connector.get_orders(
                start_date=today,
                end_date=today,
                page_size=100
            )
            
            total_orders = orders_data.get("total", 0)
            
            # 尝试获取订单统计
            try:
                stats = await erp_connector.get_orders_stats()
            except:
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
            logger.error(f"[小助] 查询ERP数据失败: {e}")
            return {"success": True, "response": "📊 ERP数据查询暂时不可用，请检查ERP连接配置。"}
    
    # ==================== 日报汇总 ====================
    
    async def _handle_daily_report(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理每日简报请求"""
        await self.log_live_step("think", "生成每日简报", "汇总日程、订单、邮件")
        
        lines = ["📋 今日简报", "━" * 18]
        
        # 1. 今日日程
        schedule_result = await self._handle_schedule_query("今天", {}, user_id)
        
        # 2. 待办事项
        todo_result = await self._handle_todo_query("", {}, user_id)
        
        # 3. 订单数据（简化）
        try:
            from app.services.erp_connector import erp_connector
            today = datetime.now().strftime("%Y-%m-%d")
            orders_data = await erp_connector.get_orders(start_date=today, end_date=today, page_size=1)
            order_count = orders_data.get("total", 0)
            lines.append(f"\n📦 今日订单: {order_count}单")
        except:
            pass
        
        # 4. 邮件统计（简化）
        try:
            from app.services.multi_email_service import multi_email_service
            summary = await multi_email_service.get_unread_summary()
            lines.append(f"📧 未读邮件: {summary['total_unread']}封")
        except:
            pass
        
        return {"success": True, "response": "\n".join(lines)}
    
    # ==================== 帮助 ====================
    
    async def _handle_help(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理帮助请求"""
        return {
            "success": True,
            "response": """🤖 我是小助，你的个人助理

📅 **日程管理**
• "明天下午3点和张总开会"
• "今天有什么安排"
• "取消明天的会议"

📋 **待办事项**
• "记得下周五交报告"
• "待办列表"

📼 **会议纪要**
• 发送会议录音给我

📧 **邮件管理**
• "查看新邮件"

📊 **业务数据**
• "今天订单情况"
• "日报"

有什么需要帮忙的？"""
        }
    
    async def _handle_unknown(self, message: str, intent: Dict, user_id: str) -> Dict[str, Any]:
        """处理无法识别的意图"""
        # 使用AI生成回复
        response = await self.chat(message, "用户向你咨询，请简洁回答或引导他使用你的功能")
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
            logger.error(f"[小助] 保存交互记录失败: {e}")
    
    # ==================== 主动推送方法 ====================
    
    async def send_tomorrow_preview(self, user_id: str) -> Optional[str]:
        """发送明日安排预览（每天晚上8点调用）"""
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
            
            # 标记已发送
            await db.execute(
                text("""
                    UPDATE assistant_schedules
                    SET reminder_sent_day_before = TRUE
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
        """获取需要发送的提醒（定时任务调用）"""
        now = datetime.now()
        reminders = []
        
        async with AsyncSessionLocal() as db:
            # 查找需要提醒的日程（提前reminder_minutes分钟）
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
                
                # 标记已发送
                await db.execute(
                    text("UPDATE assistant_schedules SET reminder_sent = TRUE WHERE id = :id"),
                    {"id": row[0]}
                )
            
            await db.commit()
        
        return reminders


# 创建单例并注册
assistant_agent = AssistantAgent()
AgentRegistry.register(assistant_agent)
