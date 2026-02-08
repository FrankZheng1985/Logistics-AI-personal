"""
ScheduleSkill - 日程管理技能

职责：
- 添加日程
- 查询日程
- 修改日程
- 生成iCal文件
- 待办管理
- 苹果日历直写
"""
import json
import re
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from loguru import logger
from sqlalchemy import text
import pytz

from app.skills.base import BaseSkill, SkillRegistry
from app.models.database import AsyncSessionLocal


CHINA_TZ = pytz.timezone('Asia/Shanghai')


class ScheduleSkill(BaseSkill):
    """日程管理技能"""

    name = "schedule"
    description = "日程管理：添加、查询、修改日程，生成iCal文件，待办管理，苹果日历直写"
    tool_names = [
        "add_schedule",
        "query_schedule",
        "update_schedule",
        "add_todo",
        "query_todo",
        "generate_ical",
        "add_to_apple_calendar",
    ]

    @staticmethod
    def _to_china_time(dt):
        """转换为中国时区时间"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(CHINA_TZ)

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        handlers = {
            "add_schedule": self._handle_schedule_add,
            "query_schedule": self._handle_schedule_query,
            "update_schedule": self._handle_schedule_update,
            "add_todo": self._handle_todo_add,
            "query_todo": self._handle_todo_query,
            "generate_ical": self._handle_generate_ical,
            "add_to_apple_calendar": self._handle_add_to_apple_calendar,
        }
        handler = handlers.get(tool_name)
        if handler:
            return await handler(message=message, user_id=user_id, args=args)
        return self._err(f"未知工具: {tool_name}")

    # ==================== 添加日程 ====================

    async def _handle_schedule_add(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """处理添加日程"""
        await self.log_step("think", "解析日程信息", "提取时间、事项、地点")

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
                return self._err("抱歉，我没能理解日程信息，请用更清晰的方式告诉我。")

            schedule_data = json.loads(json_match.group())

            start_time_str = schedule_data.get("start_time")
            start_time_dt = None
            end_time_dt = None

            if start_time_str:
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]:
                    try:
                        start_time_dt = datetime.strptime(start_time_str, fmt)
                        break
                    except Exception:
                        continue

            end_time_str = schedule_data.get("end_time")
            if end_time_str:
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]:
                    try:
                        end_time_dt = datetime.strptime(end_time_str, fmt)
                        break
                    except Exception:
                        continue

            if not start_time_dt:
                return self._err("抱歉，我没能理解日程的时间，请用更清晰的方式告诉我。")

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
                logger.warning(f"[ScheduleSkill] iCal文件生成失败（不影响日程保存）: {e}")

            response_text = f"日程已记录：{schedule_data['title']}，{time_str}{location_str}"

            result = self._ok(response_text, schedule_id=str(row[0]))
            if ical_path:
                result["filepath"] = ical_path
            return result

        except Exception as e:
            logger.error(f"[ScheduleSkill] 添加日程失败: {e}")
            return self._err(f"添加日程时出错了：{str(e)}")

    # ==================== 查询日程 ====================

    async def _handle_schedule_query(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """处理查询日程"""
        await self.log_step("search", "查询日程", "获取相关日程安排")

        china_now = datetime.now(CHINA_TZ)
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
                    "time": self._to_china_time(s[1]).strftime("%H:%M"),
                    "location": s[3],
                    "priority": s[4]
                } for s in schedules
            ]
        }

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
        return self._ok(smart_response)

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
            return self._ok(f"{label}暂无安排")

        lines = [f"{label}安排"]
        current_date = None

        for s in schedules:
            china_time = self._to_china_time(s[1])
            schedule_date = china_time.date()
            if schedule_date != current_date:
                current_date = schedule_date
                weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][schedule_date.weekday()]
                lines.append(f"\n{schedule_date.month}月{schedule_date.day}日 {weekday}")

            time_str = china_time.strftime("%H:%M")
            location_str = f" - {s[2]}" if s[2] else ""
            lines.append(f"  {time_str} {s[0]}{location_str}")

        lines.append(f"\n共{len(schedules)}项安排")
        return self._ok("\n".join(lines))

    # ==================== 修改日程 ====================

    async def _handle_schedule_update(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """处理修改日程"""
        await self.log_step("think", "解析修改请求", "识别要修改的日程和新信息")

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
                return self._err("抱歉，我没能理解您想修改什么，请更详细地描述。")

            update_data = json.loads(json_match.group())
            search_keyword = update_data.get("search_keyword", "")

            if not search_keyword:
                return self._err("请告诉我您要修改哪个日程？")

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
                return self._err(f"没有找到'{search_keyword}'相关的日程。")

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
                return self._err("没有检测到需要修改的内容。")

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
                changes.append(f"时间改为：{new_dt.month}月{new_dt.day}日 {weekday} {new_dt.strftime('%H:%M')}")
            if update_data.get("new_title"):
                changes.append(f"标题改为：{update_data['new_title']}")
            if update_data.get("new_location"):
                changes.append(f"地点改为：{update_data['new_location']}")

            response_text = f"日程已修改！{old_title}\n{chr(10).join(changes)}"
            return self._ok(response_text)

        except Exception as e:
            logger.error(f"[ScheduleSkill] 修改日程失败: {e}")
            return self._err(f"修改日程时出错了：{str(e)}")

    # ==================== 待办管理 ====================

    async def _handle_todo_add(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """处理添加待办"""
        await self.log_step("think", "解析待办信息", "提取内容和截止日期")

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
                return self._err("抱歉，我没能理解待办内容，请再说一遍？")

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
                due_str = f"\n截止：{due_date.month}月{due_date.day}日"

            return self._ok(
                f"待办已记录！\n\n{todo_data['content']}{due_str}\n\n需要我提醒你吗？",
                todo_id=str(row[0])
            )

        except Exception as e:
            logger.error(f"[ScheduleSkill] 添加待办失败: {e}")
            return self._err(f"添加待办时出错了：{str(e)}")

    async def _handle_todo_query(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
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
            return self._ok("待办列表：暂无待办事项，真棒！")

        lines = ["待办列表"]
        for i, t in enumerate(todos, 1):
            priority_icon = {"urgent": "🔴", "high": "🟡"}.get(t[1], "")
            due_str = f" (截止{t[2].month}/{t[2].day})" if t[2] else ""
            lines.append(f"{i}. {priority_icon}{t[0]}{due_str}")

        lines.append(f"\n共{len(todos)}项待办")
        return self._ok("\n".join(lines))

    # ==================== iCal 文件生成 ====================

    async def _handle_generate_ical(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """生成iCal日历文件（由LLM function calling触发）"""
        events = args.get("events", []) if args else []

        if not events:
            return self._err("没有提供日程事件")

        # 解析事件
        parsed_events = []
        first_title = "日程"
        for ev in events:
            start_str = ev.get("start_date", "")
            start_dt = None
            end_dt = None

            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]:
                try:
                    start_dt = datetime.strptime(start_str, fmt)
                    break
                except ValueError:
                    continue

            if not start_dt:
                continue

            end_str = ev.get("end_date")
            if end_str:
                for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]:
                    try:
                        end_dt = datetime.strptime(end_str, fmt)
                        break
                    except ValueError:
                        continue

            if not first_title or first_title == "日程":
                first_title = ev.get("title", "日程")

            parsed_events.append({
                "title": ev.get("title", "日程"),
                "start_time": start_dt,
                "end_time": end_dt,
                "location": ev.get("location"),
                "description": ev.get("description"),
                "is_recurring": ev.get("is_recurring", False),
                "recurring_pattern": ev.get("recurring_pattern"),
            })

        if not parsed_events:
            return self._err("日程时间解析失败，请检查日期格式")

        filepath = self._generate_ical_file(
            title=first_title,
            start_time=parsed_events[0]["start_time"],
            events=parsed_events
        )
        return self._ok(f"iCal文件已生成，包含{len(parsed_events)}个日程", filepath=filepath)

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
        """生成 iCal (.ics) 文件，返回文件路径"""
        from icalendar import Calendar, Event, vRecur, Alarm

        cal = Calendar()
        cal.add('prodid', '-//Maria AI Assistant//CN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')

        china_tz = pytz.timezone('Asia/Shanghai')

        def _add_event(cal, title, start, end=None, location=None, description=None, recurring=False, pattern=None):
            event = Event()
            event.add('summary', title)
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

            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', f'提醒：{title}')
            alarm.add('trigger', timedelta(minutes=-15))
            event.add_component(alarm)

            if recurring and pattern:
                pattern_lower = pattern.lower() if pattern else ""
                if "每周" in pattern_lower or "weekly" in pattern_lower:
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

        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)[:30]
        filepath = f"/tmp/documents/{safe_title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.ics"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'wb') as f:
            f.write(cal.to_ical())

        logger.info(f"[ScheduleSkill] iCal文件已生成: {filepath}")
        return filepath

    # ==================== 苹果日历直写 ====================

    async def _handle_add_to_apple_calendar(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """直接往苹果日历里写入事件（通过 CalDAV）"""
        from app.services.caldav_service import apple_calendar

        events_raw = args.get("events", []) if args else []
        if not events_raw:
            return self._err("没有提供日程事件")

        events = []
        for ev in events_raw:
            start_str = ev.get("start_date", "")
            start_dt = None
            end_dt = None

            for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]:
                try:
                    start_dt = datetime.strptime(start_str, fmt)
                    break
                except ValueError:
                    continue

            if not start_dt:
                logger.warning(f"[ScheduleSkill] 日程时间解析失败: {start_str}")
                continue

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
            return self._err("日程时间解析失败，请检查日期格式")

        try:
            result = await apple_calendar.add_events(events)
            logger.info(f"[ScheduleSkill] 苹果日历写入结果: {result['message']}")
            return result
        except Exception as e:
            logger.error(f"[ScheduleSkill] 苹果日历写入失败: {e}")
            return self._err(f"写入苹果日历失败: {str(e)}")


# 注册
SkillRegistry.register(ScheduleSkill())
