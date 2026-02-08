"""
Apple CalDAV 日历服务
通过 CalDAV 协议直接读写老板的 iCloud 日历。
仅操作指定的日历，不碰其他任何数据。
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger


class AppleCalendarService:
    """Apple iCloud 日历服务（CalDAV）"""

    def __init__(self):
        self._client = None
        self._calendar = None
        self._calendar_name = None

    def _get_client(self):
        """获取 CalDAV 客户端（懒加载）"""
        if self._client:
            return self._client

        from app.core.config import settings
        import caldav

        username = getattr(settings, 'APPLE_CALDAV_USERNAME', None)
        password = getattr(settings, 'APPLE_CALDAV_PASSWORD', None)
        url = getattr(settings, 'APPLE_CALDAV_URL', 'https://caldav.icloud.com')

        if not username or not password:
            raise ValueError("Apple CalDAV 未配置（缺少 APPLE_CALDAV_USERNAME 或 APPLE_CALDAV_PASSWORD）")

        self._client = caldav.DAVClient(
            url=url,
            username=username,
            password=password,
        )
        self._calendar_name = getattr(settings, 'APPLE_CALDAV_CALENDAR_NAME', None)
        return self._client

    def _get_calendar(self):
        """获取指定的日历（或默认日历）"""
        if self._calendar:
            return self._calendar

        client = self._get_client()
        principal = client.principal()
        calendars = principal.calendars()

        if not calendars:
            raise ValueError("未找到任何日历")

        # 如果指定了日历名称，找到对应日历
        if self._calendar_name:
            for cal in calendars:
                if cal.name == self._calendar_name:
                    self._calendar = cal
                    logger.info(f"[CalDAV] 使用指定日历: {cal.name}")
                    return self._calendar
            # 没找到指定日历，使用第一个
            logger.warning(f"[CalDAV] 未找到名为 '{self._calendar_name}' 的日历，使用默认日历")

        # 使用第一个日历
        self._calendar = calendars[0]
        logger.info(f"[CalDAV] 使用日历: {self._calendar.name}")
        return self._calendar

    def _build_vevent(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        alarm_minutes: int = 15,
        is_recurring: bool = False,
        recurring_pattern: Optional[str] = None,
    ) -> str:
        """构建 iCalendar VEVENT 字符串"""
        import uuid

        if not end_time:
            end_time = start_time + timedelta(hours=1)

        uid = str(uuid.uuid4())
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dtstart = start_time.strftime("%Y%m%dT%H%M%S")
        dtend = end_time.strftime("%Y%m%dT%H%M%S")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Maria AI Assistant//CN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART;TZID=Asia/Shanghai:{dtstart}",
            f"DTEND;TZID=Asia/Shanghai:{dtend}",
            f"SUMMARY:{title}",
        ]

        if location:
            lines.append(f"LOCATION:{location}")
        if description:
            lines.append(f"DESCRIPTION:{description}")

        # 重复规则
        if is_recurring and recurring_pattern:
            rrule = self._parse_recurring_pattern(recurring_pattern)
            if rrule:
                lines.append(f"RRULE:{rrule}")

        # 提醒
        if alarm_minutes > 0:
            lines.extend([
                "BEGIN:VALARM",
                "TRIGGER:-PT{}M".format(alarm_minutes),
                "ACTION:DISPLAY",
                f"DESCRIPTION:提醒: {title}",
                "END:VALARM",
            ])

        lines.extend([
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        return "\r\n".join(lines)

    def _parse_recurring_pattern(self, pattern: str) -> Optional[str]:
        """解析中文重复规则为 RRULE"""
        pattern = pattern.strip()
        mapping = {
            "每天": "FREQ=DAILY",
            "每日": "FREQ=DAILY",
            "每周": "FREQ=WEEKLY",
            "每月": "FREQ=MONTHLY",
            "每年": "FREQ=YEARLY",
        }

        # 精确匹配
        if pattern in mapping:
            return mapping[pattern]

        # 带星期的：每周一、每周二...
        weekday_map = {
            "一": "MO", "二": "TU", "三": "WE", "四": "TH",
            "五": "FR", "六": "SA", "日": "SU", "天": "SU",
        }
        for cn, en in weekday_map.items():
            if f"每周{cn}" in pattern or f"周{cn}" in pattern:
                return f"FREQ=WEEKLY;BYDAY={en}"

        return None

    def _sync_add_event(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        alarm_minutes: int = 15,
        is_recurring: bool = False,
        recurring_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步方法：添加单个事件到日历"""
        try:
            calendar = self._get_calendar()
            vcal = self._build_vevent(
                title=title,
                start_time=start_time,
                end_time=end_time,
                location=location,
                description=description,
                alarm_minutes=alarm_minutes,
                is_recurring=is_recurring,
                recurring_pattern=recurring_pattern,
            )
            event = calendar.save_event(vcal)
            logger.info(f"[CalDAV] 事件已添加: {title} ({start_time})")
            return {
                "status": "success",
                "title": title,
                "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
                "calendar_name": getattr(calendar, 'name', '日历'),
            }
        except Exception as e:
            logger.error(f"[CalDAV] 添加事件失败: {e}")
            return {"status": "error", "message": str(e)}

    def _sync_add_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """同步方法：批量添加多个事件"""
        results = []
        success_count = 0
        fail_count = 0

        for ev in events:
            result = self._sync_add_event(
                title=ev["title"],
                start_time=ev["start_time"],
                end_time=ev.get("end_time"),
                location=ev.get("location"),
                description=ev.get("description"),
                alarm_minutes=ev.get("alarm_minutes", 15),
                is_recurring=ev.get("is_recurring", False),
                recurring_pattern=ev.get("recurring_pattern"),
            )
            results.append(result)
            if result["status"] == "success":
                success_count += 1
            else:
                fail_count += 1

        return {
            "status": "success" if fail_count == 0 else "partial",
            "total": len(events),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results,
            "message": f"成功添加 {success_count}/{len(events)} 个日程到苹果日历"
        }

    def _sync_list_calendars(self) -> List[Dict[str, str]]:
        """同步方法：列出所有可用日历"""
        client = self._get_client()
        principal = client.principal()
        calendars = principal.calendars()
        return [{"name": cal.name, "id": str(cal.id)} for cal in calendars]

    def _sync_query_events(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """同步方法：查询日期范围内的事件"""
        calendar = self._get_calendar()
        events = calendar.date_search(start=start, end=end, expand=True)
        
        results = []
        for event in events:
            try:
                vevent = event.vobject_instance.vevent
                results.append({
                    "title": str(vevent.summary.value) if hasattr(vevent, 'summary') else "无标题",
                    "start": str(vevent.dtstart.value) if hasattr(vevent, 'dtstart') else "",
                    "end": str(vevent.dtend.value) if hasattr(vevent, 'dtend') else "",
                    "location": str(vevent.location.value) if hasattr(vevent, 'location') else "",
                })
            except Exception:
                continue
        return results

    # ==================== 异步接口（供 Maria 调用）====================

    async def add_event(self, **kwargs) -> Dict[str, Any]:
        """异步添加单个事件"""
        return await asyncio.to_thread(self._sync_add_event, **kwargs)

    async def add_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """异步批量添加事件"""
        return await asyncio.to_thread(self._sync_add_events, events)

    async def list_calendars(self) -> List[Dict[str, str]]:
        """异步列出日历"""
        return await asyncio.to_thread(self._sync_list_calendars)

    async def query_events(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        """异步查询事件"""
        return await asyncio.to_thread(self._sync_query_events, start, end)

    async def check_connection(self) -> Dict[str, Any]:
        """检查 CalDAV 连接是否正常"""
        try:
            calendars = await self.list_calendars()
            return {
                "status": "success",
                "connected": True,
                "calendars": calendars,
                "message": f"已连接，共有 {len(calendars)} 个日历"
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "message": f"连接失败: {str(e)}"
            }


# 全局单例
apple_calendar = AppleCalendarService()
