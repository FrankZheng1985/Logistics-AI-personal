"""
DocumentSkill - 文档生成技能

职责：
- 生成PPT
- 生成Word文档
- 生成代码
- 生成工作总结/日报/周报
"""
from datetime import datetime
from typing import Dict, Any
from loguru import logger

from app.skills.base import BaseSkill, SkillRegistry
from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class DocumentSkill(BaseSkill):
    """文档生成技能"""

    name = "document"
    description = "文档生成：PPT、Word、代码、工作总结、日报、周报"
    tool_names = [
        "generate_ppt",
        "generate_word",
        "generate_code",
        "generate_work_summary",
        "query_daily_report",
    ]

    async def handle(self, tool_name: str, args: Dict[str, Any],
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        handlers = {
            "generate_ppt": self._handle_generate_ppt,
            "generate_word": self._handle_generate_word,
            "generate_code": self._handle_generate_code,
            "generate_work_summary": self._handle_daily_summary,
            "query_daily_report": self._handle_daily_report,
        }
        handler = handlers.get(tool_name)
        if handler:
            return await handler(message=message, user_id=user_id, args=args)
        return self._err(f"未知工具: {tool_name}")

    # ==================== PPT ====================

    async def _handle_generate_ppt(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """生成PPT演示文稿"""
        await self.log_step("think", "准备生成PPT", "分析主题和要求")

        from app.services.document_service import document_service

        if len(message) < 15:
            context = f"用户说：{message}\n用户想做PPT但信息不够详细。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。他想做PPT但说得不够具体，随意问问主题和大概要几页就行。短句，口语，不要用markdown。"
            )
            return self._ok(smart_response)

        await self.log_step("think", "正在生成PPT", "大约需要30秒")
        result = await document_service.generate_ppt(topic=message, requirements="", slides_count=10)

        if result.get("success"):
            context = f"PPT已经生成好了，标题是《{result.get('title')}》，一共{result.get('slides_count')}页。文件会自动发送到聊天窗口。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。PPT做好了已经发过去了，简单说一句标题和页数，问要不要改。绝对不要提文件路径。短句口语。"
            )
            return self._ok(smart_response, filepath=result.get("filepath"))
        else:
            return self._err(f"PPT生成遇到了点问题：{result.get('error')}。要不我换个方式帮您试试？")

    # ==================== Word ====================

    async def _handle_generate_word(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """生成Word文档"""
        await self.log_step("think", "准备生成文档", "分析主题和要求")

        from app.services.document_service import document_service

        if len(message) < 10:
            context = f"用户说：{message}\n用户想写文档但信息不够。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。他想写文档但信息不够，随意问问写什么主题、大概什么方向就行。短句口语，不要用markdown。"
            )
            return self._ok(smart_response)

        await self.log_step("think", "正在撰写文档", "大约需要1分钟")
        result = await document_service.generate_word(topic=message)

        if result.get("success"):
            context = f"Word文档已经写好了，标题是《{result.get('title')}》，一共{result.get('sections_count')}个章节。文件会自动发送到聊天窗口。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。文档写好了已经发过去了，简单说一句标题和大概内容，问要不要改。绝对不要提文件路径。短句口语。"
            )
            return self._ok(smart_response, filepath=result.get("filepath"))
        else:
            return self._err(f"文档生成遇到了点问题：{result.get('error')}。我再帮您试试~")

    # ==================== 代码 ====================

    async def _handle_generate_code(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """帮老板写代码"""
        await self.log_step("think", "分析代码需求", "准备编写代码")

        from app.services.document_service import document_service

        if len(message) < 10:
            context = f"用户说：{message}\n用户想写代码但需求不清楚。"
            smart_response = await self.chat(
                context,
                "你是郑总的私人助理。他想写代码但没说清楚要什么，问问想实现什么功能就行。短句口语。"
            )
            return self._ok(smart_response)

        language = "python"
        if any(kw in message.lower() for kw in ["javascript", "js", "前端", "react", "vue"]):
            language = "javascript"
        elif any(kw in message.lower() for kw in ["sql", "数据库", "查询"]):
            language = "sql"

        result = await document_service.generate_code(requirement=message, language=language)

        if result.get("success"):
            return self._ok(result["code"])
        else:
            return self._err("代码写的时候遇到了点问题，我再试一下~")

    # ==================== 工作总结 ====================

    async def _handle_daily_summary(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """生成日报/今日总结"""
        await self.log_step("think", "汇总今日数据", "正在生成工作总结")

        try:
            from app.services.summary_service import summary_service
            summary = await summary_service.generate_daily_summary()
            return self._ok(summary)
        except Exception as e:
            logger.error(f"[DocumentSkill] 日报生成失败: {e}")
            return self._ok("今日数据还在汇总中，我整理好了发给您~")

    # ==================== 每日简报 ====================

    async def _handle_daily_report(self, message: str, user_id: str, args: Dict = None) -> Dict[str, Any]:
        """处理每日简报请求"""
        await self.log_step("think", "生成每日简报", "汇总日程、订单、邮件、AI团队")

        lines = ["今日简报"]

        # 日程
        try:
            from app.skills.schedule import ScheduleSkill
            schedule_skill = SkillRegistry.get("schedule")
            if schedule_skill:
                schedule_result = await schedule_skill.handle("query_schedule", {}, message="今天", user_id=user_id)
        except Exception:
            pass

        # 订单数据
        try:
            from app.services.erp_connector import erp_connector
            today = datetime.now().strftime("%Y-%m-%d")
            orders_data = await erp_connector.get_orders(start_date=today, end_date=today, page_size=1)
            order_count = orders_data.get("total", 0)
            lines.append(f"\n今日订单: {order_count}单")
        except Exception:
            pass

        # 邮件统计
        try:
            from app.services.multi_email_service import multi_email_service
            summary = await multi_email_service.get_unread_summary()
            lines.append(f"未读邮件: {summary['total_unread']}封")
        except Exception:
            pass

        # AI团队
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
                    lines.append(f"AI团队今日: {task_stats[1]}/{task_stats[0]} 任务完成")
        except Exception:
            pass

        return self._ok("\n".join(lines))


# 注册
SkillRegistry.register(DocumentSkill())
