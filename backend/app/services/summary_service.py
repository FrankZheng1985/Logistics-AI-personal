"""
工作总结引擎 - 日报/周报/月报自动生成
Clauwdbot 的智能汇总能力
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import json

from app.core.llm import chat_completion
from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class SummaryService:
    """工作总结生成服务"""
    
    async def _get_schedule_data(self, start_date, end_date) -> list:
        """获取日程数据"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT title, start_time, location, is_completed
                        FROM assistant_schedules
                        WHERE DATE(start_time) BETWEEN :start AND :end
                        ORDER BY start_time ASC
                    """),
                    {"start": start_date, "end": end_date}
                )
                return [{"title": r[0], "time": str(r[1]), "location": r[2], "done": r[3]} for r in result.fetchall()]
        except Exception as e:
            logger.warning(f"[Summary] 获取日程数据失败: {e}")
            return []
    
    async def _get_task_data(self, start_date, end_date) -> list:
        """获取AI任务数据"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT agent_type, status, COUNT(*) as cnt
                        FROM ai_tasks
                        WHERE created_at BETWEEN :start AND :end
                        GROUP BY agent_type, status
                        ORDER BY agent_type
                    """),
                    {"start": start_date, "end": end_date}
                )
                return [{"agent": r[0], "status": r[1], "count": r[2]} for r in result.fetchall()]
        except Exception as e:
            logger.warning(f"[Summary] 获取任务数据失败: {e}")
            return []
    
    async def _get_interaction_data(self, start_date, end_date) -> dict:
        """获取交互统计"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT interaction_type, COUNT(*) as cnt
                        FROM assistant_interactions
                        WHERE created_at BETWEEN :start AND :end
                        GROUP BY interaction_type
                        ORDER BY cnt DESC
                    """),
                    {"start": start_date, "end": end_date}
                )
                return {r[0]: r[1] for r in result.fetchall()}
        except Exception as e:
            logger.warning(f"[Summary] 获取交互数据失败: {e}")
            return {}
    
    async def _get_lead_data(self, start_date, end_date) -> dict:
        """获取线索数据"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT COUNT(*) as total,
                               COUNT(CASE WHEN intent_score >= 60 THEN 1 END) as high_intent
                        FROM potential_customers
                        WHERE created_at BETWEEN :start AND :end
                    """),
                    {"start": start_date, "end": end_date}
                )
                row = result.fetchone()
                if row:
                    return {"total": row[0], "high_intent": row[1]}
                return {"total": 0, "high_intent": 0}
        except Exception as e:
            logger.warning(f"[Summary] 获取线索数据失败: {e}")
            return {"total": 0, "high_intent": 0}
    
    async def generate_daily_summary(self, date: datetime = None) -> str:
        """
        生成日报（口语化，给老板看的）
        
        Args:
            date: 目标日期，默认今天
        
        Returns:
            口语化的日报文本
        """
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        # 并行获取各维度数据
        schedules = await self._get_schedule_data(start.date(), start.date())
        tasks = await self._get_task_data(start, end)
        interactions = await self._get_interaction_data(start, end)
        leads = await self._get_lead_data(start, end)
        
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][start.weekday()]
        
        raw_data = {
            "date": start.strftime("%Y-%m-%d"),
            "weekday": weekday,
            "schedules": schedules,
            "ai_tasks": tasks,
            "interactions": interactions,
            "leads": leads
        }
        
        summary_prompt = f"""你是Clauwdbot，温柔利索的AI女助理。请根据以下数据生成今日工作总结给郑总看。

数据：
{json.dumps(raw_data, ensure_ascii=False, indent=2)}

要求：
1. 像在微信上跟老板汇报一样自然
2. 先说最重要的（业绩相关的数据）
3. 然后说团队表现
4. 最后给一个明天的建议或提醒
5. 不要用markdown、标签、列表符号、分隔线
6. 语气温柔但信息到位
7. 不超过300字"""

        try:
            summary = await chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.7,
                max_tokens=800
            )
            return summary
        except Exception as e:
            logger.error(f"[Summary] 生成日报失败: {e}")
            return "郑总，今天的总结数据还在汇总中，稍后给您发哦~"
    
    async def generate_weekly_summary(self, end_date: datetime = None) -> str:
        """
        生成周报
        
        Args:
            end_date: 周报截止日期，默认今天
        
        Returns:
            口语化的周报文本
        """
        if end_date is None:
            end_date = datetime.now()
        
        start_date = end_date - timedelta(days=7)
        start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end_date.replace(hour=23, minute=59, second=59)
        
        # 获取一周的数据
        schedules = await self._get_schedule_data(start.date(), end.date())
        tasks = await self._get_task_data(start, end)
        leads = await self._get_lead_data(start, end)
        interactions = await self._get_interaction_data(start, end)
        
        raw_data = {
            "period": f"{start.strftime('%m/%d')} - {end.strftime('%m/%d')}",
            "total_schedules": len(schedules),
            "completed_schedules": sum(1 for s in schedules if s.get("done")),
            "ai_tasks": tasks,
            "leads": leads,
            "total_interactions": sum(interactions.values()),
            "top_interactions": dict(list(interactions.items())[:5])
        }
        
        summary_prompt = f"""你是Clauwdbot，温柔利索的AI女助理。请根据以下一周数据生成周报给郑总看。

数据：
{json.dumps(raw_data, ensure_ascii=False, indent=2)}

要求：
1. 像在微信上跟老板做周汇报
2. 先说这周的关键成果
3. 分析哪些方面做得好、哪些需要改进
4. 给出下周的重点建议
5. 语气温柔但有深度
6. 不要用markdown格式
7. 不超过500字"""

        try:
            summary = await chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                use_advanced=True,
                temperature=0.7,
                max_tokens=1200
            )
            return summary
        except Exception as e:
            logger.error(f"[Summary] 生成周报失败: {e}")
            return "郑总，这周的数据还在汇总中，我整理好了发给您~"


# 单例
summary_service = SummaryService()
