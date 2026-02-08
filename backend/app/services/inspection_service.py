"""
Maria 巡检服务 - 自动检查系统各项指标，发现问题主动汇报
像公司管家一样巡视每个角落：员工表现、系统健康、异常模式

只在发现问题或优化建议时推送，没事不打扰老板。
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
import json

from app.models.database import AsyncSessionLocal
from sqlalchemy import text
from app.core.llm import chat_completion


class InspectionService:
    """系统巡检服务"""
    
    # 员工名称映射
    AGENT_NAMES = {
        "coordinator": "小调",
        "video_creator": "小影",
        "copywriter": "小文",
        "sales": "小销",
        "follow": "小跟",
        "analyst": "小析",
        "lead_hunter": "小猎",
        "analyst2": "小析2",
        "eu_customs_monitor": "小欧间谍",
    }
    
    async def run_inspection(self) -> Optional[str]:
        """
        主巡检入口 - 收集所有数据，LLM 分析，有问题才返回报告
        
        Returns:
            报告文字（有问题时），None（一切正常时）
        """
        logger.info("[巡检] 开始系统巡检...")
        
        findings = []
        
        # 1. 检查 AI 员工表现
        agent_findings = await self._check_agent_performance()
        if agent_findings:
            findings.append(("员工表现", agent_findings))
        
        # 2. 检查系统健康
        system_findings = await self._check_system_health()
        if system_findings:
            findings.append(("系统健康", system_findings))
        
        # 3. 检查异常模式
        error_findings = await self._check_error_patterns()
        if error_findings:
            findings.append(("异常模式", error_findings))
        
        # 4. 检查定时任务
        scheduler_findings = await self._check_scheduler_health()
        if scheduler_findings:
            findings.append(("定时任务", scheduler_findings))
        
        if not findings:
            logger.info("[巡检] 一切正常，无需汇报")
            return None
        
        # 有发现 -> 用 LLM 生成人话报告
        report = await self._analyze_and_report(findings)
        logger.info(f"[巡检] 发现 {len(findings)} 类问题，已生成报告")
        return report
    
    async def _check_agent_performance(self) -> Optional[str]:
        """检查AI员工表现：完成率、失败率、活跃度"""
        try:
            async with AsyncSessionLocal() as db:
                # 今日任务统计
                result = await db.execute(
                    text("""
                        SELECT 
                            agent_type,
                            COUNT(*) as total,
                            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                        FROM ai_tasks
                        WHERE created_at >= CURRENT_DATE
                        GROUP BY agent_type
                    """)
                )
                today_stats = result.fetchall()
                
                # 员工活跃度
                result = await db.execute(
                    text("""
                        SELECT name, agent_type, last_active_at, tasks_completed_today
                        FROM ai_agents
                        ORDER BY agent_type
                    """)
                )
                agents = result.fetchall()
            
            issues = []
            
            # 检查失败率
            for row in today_stats:
                agent_type, total, completed, failed = row[0], row[1], row[2], row[3]
                name = self.AGENT_NAMES.get(agent_type, agent_type)
                if total > 0 and failed > 0:
                    fail_rate = failed / total * 100
                    if fail_rate > 30:
                        issues.append(f"{name}今天{total}个任务里失败了{failed}个（失败率{fail_rate:.0f}%）")
                    elif failed >= 3:
                        issues.append(f"{name}今天失败了{failed}次任务")
            
            # 检查不活跃的员工
            now = datetime.utcnow()
            for agent in agents:
                name, agent_type, last_active, today_tasks = agent[0], agent[1], agent[2], agent[3]
                if last_active:
                    inactive_hours = (now - last_active).total_seconds() / 3600
                    if inactive_hours > 24:
                        days = int(inactive_hours / 24)
                        issues.append(f"{name}已经{days}天没活动了")
            
            return "\n".join(issues) if issues else None
            
        except Exception as e:
            logger.error(f"[巡检] 检查员工表现失败: {e}")
            return None
    
    async def _check_system_health(self) -> Optional[str]:
        """检查系统健康：数据库、API可用性"""
        issues = []
        
        try:
            # 检查数据库连接
            async with AsyncSessionLocal() as db:
                result = await db.execute(text("SELECT 1"))
                result.fetchone()
        except Exception as e:
            issues.append(f"数据库连接异常: {str(e)[:100]}")
        
        try:
            # 检查最近的 API 状态记录
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    text("""
                        SELECT api_name, status, response_time_ms, checked_at, error_message
                        FROM api_status_logs
                        WHERE checked_at >= NOW() - INTERVAL '6 hours'
                        ORDER BY checked_at DESC
                        LIMIT 20
                    """)
                )
                api_logs = result.fetchall()
            
            # 分析 API 问题
            api_issues = {}
            for log in api_logs:
                api_name, status, response_time, checked_at, error = log[0], log[1], log[2], log[3], log[4]
                if status != 'healthy' and status != 'ok':
                    if api_name not in api_issues:
                        api_issues[api_name] = 0
                    api_issues[api_name] += 1
            
            for api_name, fail_count in api_issues.items():
                if fail_count >= 2:
                    issues.append(f"{api_name} 最近6小时内异常了{fail_count}次")
                    
        except Exception as e:
            # api_status_logs 表可能不存在，忽略
            logger.debug(f"[巡检] API状态检查跳过: {e}")
        
        return "\n".join(issues) if issues else None
    
    async def _check_error_patterns(self) -> Optional[str]:
        """检查异常模式：重复错误、连续失败"""
        try:
            async with AsyncSessionLocal() as db:
                # 最近24小时的失败任务
                result = await db.execute(
                    text("""
                        SELECT agent_type, error_message, COUNT(*) as cnt
                        FROM ai_tasks
                        WHERE status = 'failed'
                        AND created_at >= NOW() - INTERVAL '24 hours'
                        AND error_message IS NOT NULL
                        GROUP BY agent_type, error_message
                        HAVING COUNT(*) >= 3
                        ORDER BY cnt DESC
                        LIMIT 5
                    """)
                )
                repeated_errors = result.fetchall()
            
            if not repeated_errors:
                return None
            
            issues = []
            for row in repeated_errors:
                agent_type, error_msg, count = row[0], row[1], row[2]
                name = self.AGENT_NAMES.get(agent_type, agent_type)
                short_error = error_msg[:80] if error_msg else "未知错误"
                issues.append(f"{name}重复报错{count}次：{short_error}")
            
            return "\n".join(issues)
            
        except Exception as e:
            logger.debug(f"[巡检] 异常模式检查跳过: {e}")
            return None
    
    async def _check_scheduler_health(self) -> Optional[str]:
        """检查定时任务健康状态"""
        try:
            from app.scheduler import get_jobs
            jobs = get_jobs()
            
            issues = []
            now = datetime.now()
            
            for job in jobs:
                # 检查是否有任务卡住（下次运行时间已经过了很久）
                if job.get("next_run_time"):
                    next_run = datetime.fromisoformat(job["next_run_time"])
                    if next_run.tzinfo:
                        from datetime import timezone
                        now_tz = now.replace(tzinfo=next_run.tzinfo)
                    else:
                        now_tz = now
                    
                    # 如果任务已经暂停
                    if job.get("pending"):
                        issues.append(f"定时任务「{job['name']}」处于暂停状态")
            
            return "\n".join(issues) if issues else None
            
        except Exception as e:
            logger.debug(f"[巡检] 定时任务检查跳过: {e}")
            return None
    
    async def _analyze_and_report(self, findings: List[tuple]) -> str:
        """把巡检数据交给 LLM，生成口语化报告"""
        
        findings_text = ""
        for category, detail in findings:
            findings_text += f"\n【{category}】\n{detail}\n"
        
        prompt = f"""你是郑总的私人助理Maria。你刚巡检完公司的AI系统，发现了一些问题。
请用微信聊天的口吻告诉郑总，简洁直接，不要用markdown、标签、分隔线。
只说发现的问题和你的建议，3-8句话就够了。
如果问题不严重可以轻松一点，如果问题严重就认真一点。

巡检发现：
{findings_text}

当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"""
        
        try:
            report = await chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            return report
        except Exception as e:
            # LLM 失败就直接用原始数据
            logger.error(f"[巡检] LLM分析失败: {e}")
            lines = ["郑总，巡检发现几个问题："]
            for category, detail in findings:
                lines.append(detail)
            return "\n".join(lines)


# 单例
inspection_service = InspectionService()


# ==================== 定时任务入口 ====================

async def run_maria_inspection():
    """定时任务调用入口 - 巡检并推送结果"""
    try:
        report = await inspection_service.run_inspection()
        
        if report:
            # 有问题，推送给老板
            from app.core.config import settings
            from app.api.wechat_assistant import send_text_message
            
            boss_users = getattr(settings, 'WECHAT_BOSS_USERS', 'Frank.Z').split(',')
            for boss_id in boss_users:
                boss_id = boss_id.strip()
                if boss_id:
                    await send_text_message(boss_id, report)
                    logger.info(f"[巡检] 已推送巡检报告给 {boss_id}")
        
    except Exception as e:
        logger.error(f"[巡检] 巡检任务执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
