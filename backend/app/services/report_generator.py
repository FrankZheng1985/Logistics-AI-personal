"""
报告生成服务
负责：AI员工工作报告、系统健康报告、业务指标报告
达到专业经理人水平的报告质量
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from loguru import logger

from app.models.database import AsyncSessionLocal
from app.services.system_monitor import system_monitor


class ReportGenerator:
    """报告生成器 - 专业经理人级别的报告系统"""
    
    async def generate_daily_report(
        self, 
        report_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """生成每日工作报告"""
        if report_date is None:
            report_date = datetime.now()
        
        date_str = report_date.strftime("%Y-%m-%d")
        start_time = datetime.now()
        
        logger.info(f"开始生成每日报告: {date_str}")
        
        # 收集各项数据
        agent_stats = await self._get_agent_work_stats(report_date)
        system_health = await system_monitor.get_system_health_summary()
        business_metrics = await self._get_business_metrics(report_date)
        
        # 生成报告摘要
        summary = self._generate_summary(agent_stats, system_health, business_metrics)
        
        # 识别亮点和问题
        highlights = self._identify_highlights(agent_stats, business_metrics)
        issues = self._identify_issues(agent_stats, system_health, business_metrics)
        recommendations = self._generate_recommendations(issues)
        
        report = {
            "report_type": "daily",
            "report_date": date_str,
            "generated_at": datetime.now().isoformat(),
            "generation_time_ms": int((datetime.now() - start_time).total_seconds() * 1000),
            
            "summary": summary,
            "highlights": highlights,
            "issues": issues,
            "recommendations": recommendations,
            
            "agent_stats": agent_stats,
            "system_health": system_health,
            "business_metrics": business_metrics
        }
        
        # 保存报告
        await self._save_report(report)
        
        logger.info(f"每日报告生成完成: {date_str}")
        
        return report
    
    async def _get_agent_work_stats(
        self, 
        report_date: datetime
    ) -> Dict[str, Any]:
        """获取AI员工工作统计"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                # 获取每个员工的任务统计
                result = await db.execute(
                    text("""
                        SELECT 
                            agent_type,
                            agent_name,
                            COUNT(*) as total_tasks,
                            COUNT(*) FILTER (WHERE status = 'success') as success_count,
                            COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                            AVG(duration_ms) as avg_duration_ms,
                            MAX(completed_at) as last_task_time
                        FROM agent_work_logs
                        WHERE DATE(created_at) = :date
                        GROUP BY agent_type, agent_name
                        ORDER BY total_tasks DESC
                    """),
                    {"date": report_date.date()}
                )
                
                rows = result.fetchall()
                
                agents = {}
                total_tasks = 0
                total_success = 0
                
                for row in rows:
                    agent_type = row[0]
                    success_rate = (row[3] / row[2] * 100) if row[2] > 0 else 0
                    
                    agents[agent_type] = {
                        "name": row[1],
                        "total_tasks": row[2],
                        "success_count": row[3],
                        "failed_count": row[4],
                        "success_rate": round(success_rate, 1),
                        "avg_duration_ms": int(row[5]) if row[5] else 0,
                        "last_task_time": row[6].isoformat() if row[6] else None,
                        "performance_rating": self._rate_performance(success_rate, row[2])
                    }
                    
                    total_tasks += row[2]
                    total_success += row[3]
                
                overall_success_rate = (total_success / total_tasks * 100) if total_tasks > 0 else 0
                
                return {
                    "date": report_date.strftime("%Y-%m-%d"),
                    "agents": agents,
                    "total_tasks": total_tasks,
                    "total_success": total_success,
                    "overall_success_rate": round(overall_success_rate, 1),
                    "active_agents": len(agents)
                }
                
        except Exception as e:
            logger.error(f"获取员工统计失败: {e}")
            return {
                "date": report_date.strftime("%Y-%m-%d"),
                "agents": {},
                "total_tasks": 0,
                "error": str(e)
            }
    
    async def _get_business_metrics(
        self, 
        report_date: datetime
    ) -> Dict[str, Any]:
        """获取业务指标"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                # 客户相关指标
                customers_result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) FILTER (WHERE DATE(created_at) = :date) as new_customers,
                            COUNT(*) FILTER (WHERE intent_level IN ('S', 'A') AND DATE(updated_at) = :date) as high_intent,
                            COUNT(*) as total_customers
                        FROM customers
                    """),
                    {"date": report_date.date()}
                )
                customers = customers_result.fetchone()
                
                # 线索相关指标
                leads_result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) FILTER (WHERE DATE(created_at) = :date) as new_leads,
                            COUNT(*) FILTER (WHERE quality_score >= 60 AND DATE(created_at) = :date) as quality_leads,
                            COUNT(*) as total_leads
                        FROM leads
                    """),
                    {"date": report_date.date()}
                )
                leads = leads_result.fetchone()
                
                # 视频相关指标
                videos_result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) FILTER (WHERE DATE(created_at) = :date) as videos_created,
                            COUNT(*) FILTER (WHERE status = 'completed' AND DATE(created_at) = :date) as videos_completed,
                            COUNT(*) as total_videos
                        FROM videos
                    """),
                    {"date": report_date.date()}
                )
                videos = videos_result.fetchone()
                
                # 对话相关指标
                conversations_result = await db.execute(
                    text("""
                        SELECT 
                            COUNT(*) as total_conversations,
                            COUNT(DISTINCT customer_id) as unique_customers
                        FROM conversations
                        WHERE DATE(created_at) = :date
                    """),
                    {"date": report_date.date()}
                )
                conversations = conversations_result.fetchone()
                
                return {
                    "date": report_date.strftime("%Y-%m-%d"),
                    "customers": {
                        "new_today": customers[0] if customers else 0,
                        "high_intent_today": customers[1] if customers else 0,
                        "total": customers[2] if customers else 0
                    },
                    "leads": {
                        "new_today": leads[0] if leads else 0,
                        "quality_leads_today": leads[1] if leads else 0,
                        "total": leads[2] if leads else 0
                    },
                    "videos": {
                        "created_today": videos[0] if videos else 0,
                        "completed_today": videos[1] if videos else 0,
                        "total": videos[2] if videos else 0
                    },
                    "conversations": {
                        "total_today": conversations[0] if conversations else 0,
                        "unique_customers": conversations[1] if conversations else 0
                    }
                }
                
        except Exception as e:
            logger.error(f"获取业务指标失败: {e}")
            return {"date": report_date.strftime("%Y-%m-%d"), "error": str(e)}
    
    def _generate_summary(
        self,
        agent_stats: Dict[str, Any],
        system_health: Dict[str, Any],
        business_metrics: Dict[str, Any]
    ) -> str:
        """生成报告摘要"""
        date = agent_stats.get("date", "今日")
        total_tasks = agent_stats.get("total_tasks", 0)
        success_rate = agent_stats.get("overall_success_rate", 0)
        system_status = system_health.get("overall_status", "unknown")
        
        new_customers = business_metrics.get("customers", {}).get("new_today", 0)
        high_intent = business_metrics.get("customers", {}).get("high_intent_today", 0)
        new_leads = business_metrics.get("leads", {}).get("new_today", 0)
        
        summary = f"""【{date} AI团队工作报告摘要】

📊 工作量：AI团队今日共处理 {total_tasks} 项任务，整体成功率 {success_rate}%。

🏥 系统状态：当前系统状态为 {self._translate_status(system_status)}。

📈 业务指标：
• 新增客户 {new_customers} 位
• 高意向客户 {high_intent} 位
• 新增线索 {new_leads} 条

💡 团队表现：{self._evaluate_team_performance(agent_stats)}
"""
        return summary
    
    def _identify_highlights(
        self,
        agent_stats: Dict[str, Any],
        business_metrics: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """识别今日亮点"""
        highlights = []
        
        # 检查高绩效员工
        for agent_type, stats in agent_stats.get("agents", {}).items():
            if stats.get("success_rate", 0) >= 95 and stats.get("total_tasks", 0) >= 10:
                highlights.append({
                    "type": "performance",
                    "title": f"{stats['name']}表现出色",
                    "detail": f"完成{stats['total_tasks']}项任务，成功率{stats['success_rate']}%"
                })
        
        # 检查业务增长
        new_customers = business_metrics.get("customers", {}).get("new_today", 0)
        if new_customers >= 5:
            highlights.append({
                "type": "growth",
                "title": "客户增长强劲",
                "detail": f"今日新增{new_customers}位客户"
            })
        
        high_intent = business_metrics.get("customers", {}).get("high_intent_today", 0)
        if high_intent >= 3:
            highlights.append({
                "type": "opportunity",
                "title": "高意向客户增加",
                "detail": f"今日新增{high_intent}位高意向客户，建议重点跟进"
            })
        
        return highlights
    
    def _identify_issues(
        self,
        agent_stats: Dict[str, Any],
        system_health: Dict[str, Any],
        business_metrics: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """识别问题和风险"""
        issues = []
        
        # 检查系统问题
        system_issues = system_health.get("issues", [])
        for issue in system_issues:
            issues.append({
                "type": "system",
                "severity": "high",
                "title": "系统异常",
                "detail": issue
            })
        
        # 检查低绩效员工
        for agent_type, stats in agent_stats.get("agents", {}).items():
            success_rate = stats.get("success_rate", 100)
            if success_rate < 80 and stats.get("total_tasks", 0) >= 5:
                issues.append({
                    "type": "performance",
                    "severity": "medium",
                    "title": f"{stats['name']}成功率较低",
                    "detail": f"成功率仅{success_rate}%，需要排查原因"
                })
        
        # 检查整体成功率
        overall_rate = agent_stats.get("overall_success_rate", 100)
        if overall_rate < 85:
            issues.append({
                "type": "quality",
                "severity": "high",
                "title": "整体任务成功率下降",
                "detail": f"当前成功率{overall_rate}%，低于85%警戒线"
            })
        
        return issues
    
    def _generate_recommendations(
        self, 
        issues: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """生成改进建议"""
        recommendations = []
        
        for issue in issues:
            if issue["type"] == "system":
                recommendations.append({
                    "priority": "high",
                    "action": "检查系统组件",
                    "detail": "建议立即检查相关API和服务状态，确保系统稳定运行"
                })
            elif issue["type"] == "performance":
                recommendations.append({
                    "priority": "medium",
                    "action": "优化AI员工配置",
                    "detail": "建议检查相关员工的提示词和参数配置，优化处理逻辑"
                })
            elif issue["type"] == "quality":
                recommendations.append({
                    "priority": "high",
                    "action": "全面质量排查",
                    "detail": "建议对任务失败原因进行详细分析，制定针对性改进方案"
                })
        
        if not recommendations:
            recommendations.append({
                "priority": "low",
                "action": "保持现状",
                "detail": "系统运行良好，建议继续保持当前工作状态"
            })
        
        return recommendations
    
    def _rate_performance(self, success_rate: float, task_count: int) -> str:
        """评价员工表现"""
        if task_count < 3:
            return "数据不足"
        
        if success_rate >= 95:
            return "优秀"
        elif success_rate >= 85:
            return "良好"
        elif success_rate >= 70:
            return "一般"
        else:
            return "需改进"
    
    def _translate_status(self, status: str) -> str:
        """翻译状态"""
        mapping = {
            "healthy": "健康 ✅",
            "warning": "警告 ⚠️",
            "critical": "严重 🔴",
            "degraded": "降级 ⚠️",
            "unknown": "未知"
        }
        return mapping.get(status, status)
    
    def _evaluate_team_performance(self, agent_stats: Dict[str, Any]) -> str:
        """评价团队整体表现"""
        success_rate = agent_stats.get("overall_success_rate", 0)
        total_tasks = agent_stats.get("total_tasks", 0)
        
        if total_tasks == 0:
            return "今日暂无任务数据"
        
        if success_rate >= 95:
            return "团队表现优异，继续保持！"
        elif success_rate >= 85:
            return "团队表现良好，稳中有进。"
        elif success_rate >= 70:
            return "团队表现一般，建议关注失败任务原因。"
        else:
            return "团队表现需要改进，建议进行全面排查。"
    
    async def _save_report(self, report: Dict[str, Any]):
        """保存报告到数据库"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                await db.execute(
                    text("""
                        INSERT INTO daily_reports 
                        (report_date, report_type, agent_stats, system_health, 
                         business_metrics, summary, highlights, issues, 
                         recommendations, generated_by, generation_time_ms)
                        VALUES (:date, :type, :agent_stats, :system_health,
                                :business_metrics, :summary, :highlights, :issues,
                                :recommendations, 'coordinator', :time_ms)
                        ON CONFLICT (report_date, report_type) DO UPDATE SET
                            agent_stats = EXCLUDED.agent_stats,
                            system_health = EXCLUDED.system_health,
                            business_metrics = EXCLUDED.business_metrics,
                            summary = EXCLUDED.summary,
                            highlights = EXCLUDED.highlights,
                            issues = EXCLUDED.issues,
                            recommendations = EXCLUDED.recommendations,
                            generation_time_ms = EXCLUDED.generation_time_ms
                    """),
                    {
                        "date": report["report_date"],
                        "type": report["report_type"],
                        "agent_stats": json.dumps(report["agent_stats"]),
                        "system_health": json.dumps(report["system_health"]),
                        "business_metrics": json.dumps(report["business_metrics"]),
                        "summary": report["summary"],
                        "highlights": json.dumps(report["highlights"]),
                        "issues": json.dumps(report["issues"]),
                        "recommendations": json.dumps(report["recommendations"]),
                        "time_ms": report["generation_time_ms"]
                    }
                )
                await db.commit()
                logger.info(f"报告已保存: {report['report_date']}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
    
    async def get_latest_report(
        self, 
        report_type: str = "daily"
    ) -> Optional[Dict[str, Any]]:
        """获取最新报告"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                result = await db.execute(
                    text("""
                        SELECT report_date, agent_stats, system_health, 
                               business_metrics, summary, highlights, issues,
                               recommendations, generation_time_ms, created_at
                        FROM daily_reports
                        WHERE report_type = :type
                        ORDER BY report_date DESC
                        LIMIT 1
                    """),
                    {"type": report_type}
                )
                
                row = result.fetchone()
                if row:
                    return {
                        "report_date": str(row[0]),
                        "agent_stats": row[1],
                        "system_health": row[2],
                        "business_metrics": row[3],
                        "summary": row[4],
                        "highlights": row[5],
                        "issues": row[6],
                        "recommendations": row[7],
                        "generation_time_ms": row[8],
                        "created_at": row[9].isoformat() if row[9] else None
                    }
                return None
        except Exception as e:
            logger.error(f"获取报告失败: {e}")
            return None


# 创建服务实例
report_generator = ReportGenerator()
