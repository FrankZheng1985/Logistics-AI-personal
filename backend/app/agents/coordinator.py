"""
小调 - AI调度主管 (专业经理人升级版)
负责：任务分配、流程协调、异常处理、工作报告
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import json

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.models.database import AsyncSessionLocal
from app.core.prompts.coordinator import COORDINATOR_SYSTEM_PROMPT


class CoordinatorAgent(BaseAgent):
    """小调 - AI调度主管（专业经理人级别）
    
    核心能力：
    1. 智能任务分配与优先级管理
    2. 团队工作流程协调
    3. 异常处理与自动恢复
    4. 专业经理人级别的工作报告
    5. 系统监控与健康管理
    """
    
    name = "小调"
    agent_type = AgentType.COORDINATOR
    description = "AI调度主管 - 负责任务分配、流程协调、异常处理、工作报告"
    
    # 任务优先级定义
    PRIORITY_LEVELS = {
        "urgent": 1,      # 紧急
        "high": 2,        # 高
        "medium": 5,      # 中
        "low": 8,         # 低
        "background": 10  # 后台
    }
    
    # 任务类型到AI员工的映射
    TASK_ROUTING = {
        "video": AgentType.VIDEO_CREATOR,
        "video_script": AgentType.COPYWRITER,
        "copy": AgentType.COPYWRITER,
        "chat": AgentType.SALES,
        "follow": AgentType.FOLLOW,
        "analysis": AgentType.ANALYST,
        "lead_search": AgentType.LEAD_HUNTER
    }
    
    def _build_system_prompt(self) -> str:
        return COORDINATOR_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理调度任务
        
        Args:
            input_data: {
                "action": "dispatch/analyze/report/monitor/coordinate",
                "task_type": 任务类型,
                "task_data": 任务数据,
                "priority": 优先级,
                "report_type": 报告类型 (daily/weekly/monthly),
                ...
            }
        """
        action = input_data.get("action", "analyze")
        action_names = {
            "dispatch": "任务分配",
            "report": "生成报告",
            "monitor": "系统监控",
            "coordinate": "流程协调",
            "analyze": "任务分析"
        }
        action_name = action_names.get(action, action)
        
        # 开始任务会话（实时直播）
        await self.start_task_session(action, f"小调开始执行: {action_name}")
        
        try:
            if action == "dispatch":
                await self.log_live_step("think", f"正在分析任务分配策略", "评估各AI员工负载和能力")
                result = await self._dispatch_task(input_data)
                await self.log_live_step("result", f"任务分配完成", f"已分配给: {result.get('target_agent', '未知')}")
            elif action == "report":
                report_type = input_data.get("report_type", "daily")
                await self.log_live_step("think", f"正在生成{report_type}报告", "汇总AI团队工作数据")
                result = await self._generate_report(input_data)
                await self.log_live_step("result", f"报告生成完成", f"报告类型: {report_type}")
            elif action == "monitor":
                check_type = input_data.get("check_type", "all")
                await self.log_live_step("search", f"正在检查系统状态", f"检查类型: {check_type}")
                result = await self._monitor_system(input_data)
                status = result.get("result", {}).get("overall_status", "unknown")
                await self.log_live_step("result", f"系统监控完成", f"系统状态: {status}")
            elif action == "coordinate":
                workflow_type = input_data.get("workflow_type", "")
                await self.log_live_step("think", f"正在协调工作流", f"工作流类型: {workflow_type}")
                result = await self._coordinate_workflow(input_data)
                await self.log_live_step("result", f"工作流协调完成", f"已启动 {len(result.get('steps', []))} 个步骤")
            else:
                await self.log_live_step("think", f"正在分析任务", "评估任务内容和路由")
                result = await self._analyze_task(input_data)
                recommended = result.get("recommended_agent", "未知")
                await self.log_live_step("result", f"任务分析完成", f"推荐分配给: {recommended}")
            
            await self.end_task_session(f"完成{action_name}")
            return result
        except Exception as e:
            await self.log_live_step("error", f"执行失败", str(e))
            await self.end_task_session(error_message=str(e))
            raise
    
    async def _analyze_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析任务并决定路由"""
        task_description = input_data.get("task_description", "")
        
        analysis_prompt = f"""请分析以下任务，决定应该分配给哪个AI员工：

任务描述：{task_description}

可用的AI员工：
1. 小影 (video_creator) - 视频创作
2. 小文 (copywriter) - 文案策划
3. 小销 (sales) - 销售客服
4. 小跟 (follow) - 客户跟进
5. 小析 (analyst) - 客户分析
6. 小猎 (lead_hunter) - 线索搜索

请分析并返回JSON格式：
{{
    "recommended_agent": "agent_type",
    "task_type": "具体任务类型",
    "priority": "urgent/high/medium/low",
    "reason": "分配原因",
    "sub_tasks": ["如需分解的子任务"]
}}
"""
        
        response = await self.think([{"role": "user", "content": analysis_prompt}])
        
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            pass
        
        return {
            "recommended_agent": "sales",
            "task_type": "general",
            "priority": "medium",
            "reason": "默认分配",
            "analysis": response
        }
    
    async def _dispatch_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分配任务给指定AI员工"""
        task_type = input_data.get("task_type", "")
        target_agent = input_data.get("target_agent")
        task_data = input_data.get("task_data", {})
        priority = input_data.get("priority", "medium")
        
        # 确定目标员工
        if not target_agent:
            target_agent = self.TASK_ROUTING.get(task_type, AgentType.SALES)
        elif isinstance(target_agent, str):
            try:
                target_agent = AgentType(target_agent)
            except ValueError:
                target_agent = AgentType.SALES
        
        # 记录任务分配
        task_id = await self._record_task_dispatch(
            task_type=task_type,
            target_agent=target_agent,
            task_data=task_data,
            priority=priority
        )
        
        self.log(f"任务分配: {task_type} → {target_agent.value} (优先级: {priority})")
        
        return {
            "task_id": task_id,
            "status": "dispatched",
            "target_agent": target_agent.value,
            "priority": priority,
            "message": f"任务已分配给{self._get_agent_name(target_agent)}"
        }
    
    async def _generate_report(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成工作报告（专业经理人级别）"""
        from app.services.report_generator import report_generator
        
        report_type = input_data.get("report_type", "daily")
        report_date = input_data.get("report_date")
        
        if report_date:
            report_date = datetime.fromisoformat(report_date)
        
        self.log(f"开始生成{report_type}报告...")
        
        if report_type == "daily":
            report = await report_generator.generate_daily_report(report_date)
        else:
            # 未来支持周报、月报
            report = await report_generator.generate_daily_report(report_date)
        
        # 生成可读性强的报告文本
        readable_report = self._format_readable_report(report)
        
        self.log(f"{report_type}报告生成完成")
        
        return {
            "report_type": report_type,
            "report_date": report.get("report_date"),
            "summary": report.get("summary"),
            "readable_report": readable_report,
            "data": report,
            "generation_time_ms": report.get("generation_time_ms")
        }
    
    def _format_readable_report(self, report: Dict[str, Any]) -> str:
        """格式化为可读性强的报告"""
        lines = []
        
        # 标题
        lines.append("=" * 60)
        lines.append(f"📊 AI团队工作日报 - {report.get('report_date', '今日')}")
        lines.append("=" * 60)
        lines.append("")
        
        # 摘要
        lines.append("【报告摘要】")
        lines.append(report.get("summary", ""))
        lines.append("")
        
        # AI员工详细工作情况
        lines.append("-" * 40)
        lines.append("【AI员工工作详情】")
        lines.append("-" * 40)
        
        agent_stats = report.get("agent_stats", {})
        for agent_type, stats in agent_stats.get("agents", {}).items():
            lines.append(f"\n▸ {stats.get('name', agent_type)}")
            lines.append(f"  • 任务数量: {stats.get('total_tasks', 0)}")
            lines.append(f"  • 成功率: {stats.get('success_rate', 0)}%")
            lines.append(f"  • 平均耗时: {stats.get('avg_duration_ms', 0)}ms")
            lines.append(f"  • 绩效评级: {stats.get('performance_rating', '-')}")
        
        lines.append("")
        
        # 系统健康状态
        lines.append("-" * 40)
        lines.append("【系统健康状态】")
        lines.append("-" * 40)
        
        system_health = report.get("system_health", {})
        overall_status = system_health.get("overall_status", "unknown")
        status_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "🔴"}.get(overall_status, "❓")
        
        lines.append(f"整体状态: {status_emoji} {overall_status.upper()}")
        
        issues = system_health.get("issues", [])
        if issues:
            lines.append("\n问题列表:")
            for issue in issues:
                lines.append(f"  ⚠️ {issue}")
        else:
            lines.append("  无异常")
        
        lines.append("")
        
        # 业务指标
        lines.append("-" * 40)
        lines.append("【业务指标概览】")
        lines.append("-" * 40)
        
        business = report.get("business_metrics", {})
        customers = business.get("customers", {})
        leads = business.get("leads", {})
        videos = business.get("videos", {})
        
        lines.append(f"• 新增客户: {customers.get('new_today', 0)}")
        lines.append(f"• 高意向客户: {customers.get('high_intent_today', 0)}")
        lines.append(f"• 新增线索: {leads.get('new_today', 0)}")
        lines.append(f"• 优质线索: {leads.get('quality_leads_today', 0)}")
        lines.append(f"• 视频创作: {videos.get('completed_today', 0)}")
        
        lines.append("")
        
        # 亮点
        highlights = report.get("highlights", [])
        if highlights:
            lines.append("-" * 40)
            lines.append("【今日亮点】")
            lines.append("-" * 40)
            for h in highlights:
                lines.append(f"🌟 {h.get('title')}: {h.get('detail')}")
            lines.append("")
        
        # 问题和建议
        issues_list = report.get("issues", [])
        recommendations = report.get("recommendations", [])
        
        if issues_list:
            lines.append("-" * 40)
            lines.append("【问题与风险】")
            lines.append("-" * 40)
            for issue in issues_list:
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.get("severity"), "⚪")
                lines.append(f"{severity_emoji} {issue.get('title')}: {issue.get('detail')}")
            lines.append("")
        
        if recommendations:
            lines.append("-" * 40)
            lines.append("【改进建议】")
            lines.append("-" * 40)
            for rec in recommendations:
                priority_emoji = {"high": "❗", "medium": "📌", "low": "💡"}.get(rec.get("priority"), "•")
                lines.append(f"{priority_emoji} {rec.get('action')}")
                lines.append(f"   {rec.get('detail')}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("生成者: 小调 (AI调度主管)")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    async def _monitor_system(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """监控系统状态"""
        from app.services.system_monitor import system_monitor
        
        check_type = input_data.get("check_type", "all")
        
        self.log(f"执行系统监控: {check_type}")
        
        if check_type == "apis":
            result = await system_monitor.check_all_apis()
        elif check_type == "certificates":
            result = await system_monitor.check_certificates()
        elif check_type == "database":
            result = await system_monitor.check_database()
        else:
            result = await system_monitor.get_system_health_summary()
        
        # 如果发现严重问题，触发告警
        if result.get("overall_status") in ["critical", "unhealthy"]:
            await self._trigger_alert(result)
        
        return {
            "check_type": check_type,
            "result": result,
            "checked_at": datetime.now().isoformat()
        }
    
    async def _coordinate_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """协调复杂工作流"""
        workflow_type = input_data.get("workflow_type", "")
        context = input_data.get("context", {})
        
        # 视频创作工作流：脚本 → 视频生成 → 发布
        if workflow_type == "video_creation":
            return await self._coordinate_video_workflow(context)
        
        # 客户转化工作流：分析 → 跟进 → 转化
        elif workflow_type == "customer_conversion":
            return await self._coordinate_conversion_workflow(context)
        
        # 线索处理工作流：搜索 → 分析 → 分配
        elif workflow_type == "lead_processing":
            return await self._coordinate_lead_workflow(context)
        
        return {"message": "未知的工作流类型", "workflow_type": workflow_type}
    
    async def _coordinate_video_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调视频创作工作流"""
        steps = []
        
        # Step 1: 小文写脚本
        steps.append({
            "step": 1,
            "agent": "copywriter",
            "task": "write_video_script",
            "status": "pending"
        })
        
        # Step 2: 小影生成视频
        steps.append({
            "step": 2,
            "agent": "video_creator",
            "task": "generate_video",
            "depends_on": 1,
            "status": "pending"
        })
        
        return {
            "workflow": "video_creation",
            "steps": steps,
            "total_steps": len(steps),
            "status": "initiated"
        }
    
    async def _coordinate_conversion_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调客户转化工作流"""
        customer_id = context.get("customer_id")
        
        steps = [
            {"step": 1, "agent": "analyst", "task": "analyze_customer"},
            {"step": 2, "agent": "follow", "task": "send_follow_up", "depends_on": 1},
            {"step": 3, "agent": "sales", "task": "close_deal", "depends_on": 2}
        ]
        
        return {
            "workflow": "customer_conversion",
            "customer_id": customer_id,
            "steps": steps,
            "status": "initiated"
        }
    
    async def _coordinate_lead_workflow(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """协调线索处理工作流"""
        steps = [
            {"step": 1, "agent": "lead_hunter", "task": "search_leads"},
            {"step": 2, "agent": "analyst", "task": "score_leads", "depends_on": 1},
            {"step": 3, "agent": "coordinator", "task": "assign_leads", "depends_on": 2}
        ]
        
        return {
            "workflow": "lead_processing",
            "steps": steps,
            "status": "initiated"
        }
    
    async def _record_task_dispatch(
        self,
        task_type: str,
        target_agent: AgentType,
        task_data: Dict[str, Any],
        priority: str
    ) -> str:
        """记录任务分配"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                import uuid
                
                task_id = str(uuid.uuid4())
                
                await db.execute(
                    text("""
                        INSERT INTO ai_tasks 
                        (id, task_type, agent_type, status, priority, input_data, created_at)
                        VALUES (:id, :task_type, :agent_type, 'pending', :priority, :input_data, NOW())
                    """),
                    {
                        "id": task_id,
                        "task_type": task_type,
                        "agent_type": target_agent.value,
                        "priority": self.PRIORITY_LEVELS.get(priority, 5),
                        "input_data": json.dumps(task_data)
                    }
                )
                await db.commit()
                return task_id
        except Exception as e:
            logger.error(f"记录任务分配失败: {e}")
            return ""
    
    async def _trigger_alert(self, health_result: Dict[str, Any]):
        """触发系统告警"""
        try:
            async with AsyncSessionLocal() as db:
                from sqlalchemy import text
                
                await db.execute(
                    text("""
                        INSERT INTO notifications 
                        (type, title, content, priority, category, created_at)
                        VALUES ('system', '系统健康告警', :content, 'urgent', 'system_alert', NOW())
                    """),
                    {
                        "content": json.dumps(health_result.get("issues", []))
                    }
                )
                await db.commit()
                logger.warning(f"系统告警已触发: {health_result.get('issues')}")
        except Exception as e:
            logger.error(f"触发告警失败: {e}")
    
    def _get_agent_name(self, agent_type: AgentType) -> str:
        """获取AI员工名称"""
        names = {
            AgentType.COORDINATOR: "小调",
            AgentType.VIDEO_CREATOR: "小影",
            AgentType.COPYWRITER: "小文",
            AgentType.SALES: "小销",
            AgentType.FOLLOW: "小跟",
            AgentType.ANALYST: "小析",
            AgentType.LEAD_HUNTER: "小猎"
        }
        return names.get(agent_type, str(agent_type))
    
    # === 便捷方法：供其他模块调用 ===
    
    async def dispatch_task(
        self,
        task_type: str,
        target_agent: AgentType,
        task_data: Dict[str, Any],
        priority: int = 5
    ) -> Dict[str, Any]:
        """分配任务（便捷方法）"""
        priority_name = "medium"
        for name, value in self.PRIORITY_LEVELS.items():
            if value == priority:
                priority_name = name
                break
        
        return await self._dispatch_task({
            "task_type": task_type,
            "target_agent": target_agent,
            "task_data": task_data,
            "priority": priority_name
        })
    
    async def get_daily_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """获取每日报告（便捷方法）"""
        return await self._generate_report({
            "report_type": "daily",
            "report_date": date
        })
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态（便捷方法）"""
        return await self._monitor_system({"check_type": "all"})


# 创建单例并注册
coordinator = CoordinatorAgent()
coordinator_agent = coordinator  # 别名，兼容旧代码
AgentRegistry.register(coordinator)
