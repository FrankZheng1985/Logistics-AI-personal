"""
小调 - AI调度主管
负责任务分配、流程协调、异常处理
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
import json
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.prompts.coordinator import COORDINATOR_SYSTEM_PROMPT, TASK_ANALYSIS_PROMPT


class CoordinatorAgent(BaseAgent):
    """小调 - AI调度主管"""
    
    name = "小调"
    agent_type = AgentType.COORDINATOR
    description = "AI调度主管 - 负责任务分配、流程协调、异常处理"
    
    def _build_system_prompt(self) -> str:
        return COORDINATOR_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务分配请求
        
        Args:
            input_data: {
                "task_description": "任务描述",
                "source": "任务来源",
                "priority_hint": "优先级提示"
            }
        
        Returns:
            分配结果
        """
        task_description = input_data.get("task_description", "")
        source = input_data.get("source", "system")
        priority_hint = input_data.get("priority_hint", "normal")
        
        # 构建分析提示
        analysis_prompt = TASK_ANALYSIS_PROMPT.format(
            task_description=task_description,
            source=source,
            priority_hint=priority_hint
        )
        
        # 让小调分析任务
        response = await self.think([{"role": "user", "content": analysis_prompt}])
        
        # 解析回复
        try:
            # 提取JSON部分
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
            else:
                result = {
                    "task_type": "unknown",
                    "assigned_to": "coordinator",
                    "instructions": task_description,
                    "priority": 5,
                    "reason": "无法解析任务"
                }
        except json.JSONDecodeError:
            result = {
                "task_type": "unknown",
                "assigned_to": "coordinator",
                "instructions": task_description,
                "priority": 5,
                "reason": "JSON解析失败"
            }
        
        self.log(f"任务分配: {result['assigned_to']} - {result['task_type']}")
        return result
    
    async def dispatch_task(
        self,
        task_type: str,
        target_agent: AgentType,
        task_data: Dict[str, Any],
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        分发任务给指定的AI员工
        
        Args:
            task_type: 任务类型
            target_agent: 目标员工类型
            task_data: 任务数据
            priority: 优先级
        
        Returns:
            任务执行结果
        """
        agent = AgentRegistry.get(target_agent)
        
        if not agent:
            self.log(f"找不到员工: {target_agent}", "error")
            return {"error": f"Agent {target_agent} not found"}
        
        self.log(f"分发任务给 {agent.name}: {task_type}")
        
        try:
            result = await agent.process(task_data)
            self.log(f"{agent.name} 完成任务: {task_type}")
            return result
        except Exception as e:
            self.log(f"{agent.name} 任务失败: {e}", "error")
            return {"error": str(e)}
    
    async def handle_customer_message(
        self,
        customer_id: str,
        message: str,
        is_new_customer: bool = False
    ) -> Dict[str, Any]:
        """
        处理客户消息，决定分配给哪个员工
        
        Args:
            customer_id: 客户ID
            message: 客户消息
            is_new_customer: 是否是新客户
        
        Returns:
            处理结果
        """
        # 决定分配给谁
        if is_new_customer:
            target = AgentType.SALES  # 新客户给小销
            self.log(f"新客户咨询，分配给小销")
        else:
            # 分析消息内容决定
            analysis = await self.process({
                "task_description": f"客户消息: {message}",
                "source": "customer",
                "priority_hint": "high"
            })
            
            assigned_to = analysis.get("assigned_to", "sales")
            if "follow" in assigned_to or "跟进" in assigned_to:
                target = AgentType.FOLLOW
            else:
                target = AgentType.SALES
        
        # 分发任务
        return await self.dispatch_task(
            task_type="customer_chat",
            target_agent=target,
            task_data={
                "customer_id": customer_id,
                "message": message
            },
            priority=2  # 客户消息优先级较高
        )
    
    async def handle_video_request(
        self,
        title: str,
        description: str,
        video_type: str = "ad"
    ) -> Dict[str, Any]:
        """
        处理视频生成请求
        
        流程：小文撰写脚本 -> 小视生成视频
        """
        self.log(f"收到视频生成请求: {title}")
        
        # 第一步：让小文撰写脚本
        script_result = await self.dispatch_task(
            task_type="write_script",
            target_agent=AgentType.COPYWRITER,
            task_data={
                "title": title,
                "description": description,
                "video_type": video_type
            }
        )
        
        if "error" in script_result:
            return script_result
        
        # 第二步：让小视生成视频
        video_result = await self.dispatch_task(
            task_type="generate_video",
            target_agent=AgentType.VIDEO_CREATOR,
            task_data={
                "title": title,
                "script": script_result.get("script", ""),
                "keywords": script_result.get("keywords", [])
            }
        )
        
        return {
            "script": script_result,
            "video": video_result
        }


# 创建单例并注册
coordinator = CoordinatorAgent()
AgentRegistry.register(coordinator)
