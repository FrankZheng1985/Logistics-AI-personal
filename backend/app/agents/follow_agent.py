"""
小跟 - 跟进专员
负责老客户维护、意向客户跟进、促成转化
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.prompts.follow import FOLLOW_SYSTEM_PROMPT, FOLLOW_UP_PROMPT


class FollowAgent(BaseAgent):
    """小跟 - 跟进专员"""
    
    name = "小跟"
    agent_type = AgentType.FOLLOW
    description = "跟进专员 - 负责老客户维护、意向客户跟进、促成转化"
    
    # 跟进间隔配置（天）
    FOLLOW_INTERVALS = {
        "S": 1,   # S级每天跟进
        "A": 2,   # A级每2天
        "B": 5,   # B级每5天
        "C": 15,  # C级每15天
    }
    
    def _build_system_prompt(self) -> str:
        return FOLLOW_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理跟进任务
        
        Args:
            input_data: {
                "customer_info": "客户信息",
                "intent_level": "意向等级",
                "last_contact": "上次联系时间",
                "last_conversation": "上次对话内容",
                "purpose": "跟进目的"
            }
        
        Returns:
            {
                "follow_message": "跟进消息",
                "next_follow_time": "下次跟进时间建议"
            }
        """
        customer_info = input_data.get("customer_info", {})
        intent_level = input_data.get("intent_level", "B")
        last_contact = input_data.get("last_contact", "未知")
        last_conversation = input_data.get("last_conversation", "无记录")
        purpose = input_data.get("purpose", "日常跟进")
        
        # 生成跟进消息
        prompt = FOLLOW_UP_PROMPT.format(
            customer_info=str(customer_info),
            intent_level=intent_level,
            last_contact=last_contact,
            last_conversation=last_conversation,
            purpose=purpose
        )
        
        follow_message = await self.think([{"role": "user", "content": prompt}])
        
        # 计算下次跟进时间
        interval = self.FOLLOW_INTERVALS.get(intent_level, 7)
        next_follow = datetime.utcnow() + timedelta(days=interval)
        
        self.log(f"生成跟进消息 ({intent_level}级客户)")
        
        return {
            "follow_message": follow_message,
            "next_follow_time": next_follow.isoformat(),
            "suggested_interval_days": interval
        }
    
    async def generate_batch_follow_plan(
        self, 
        customers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量生成跟进计划
        
        Args:
            customers: 客户列表
        
        Returns:
            跟进计划列表
        """
        plans = []
        
        for customer in customers:
            intent_level = customer.get("intent_level", "B")
            last_contact_str = customer.get("last_contact_at")
            
            # 判断是否需要跟进
            if last_contact_str:
                last_contact = datetime.fromisoformat(last_contact_str.replace("Z", "+00:00"))
                days_since = (datetime.utcnow() - last_contact.replace(tzinfo=None)).days
                interval = self.FOLLOW_INTERVALS.get(intent_level, 7)
                
                if days_since >= interval:
                    plans.append({
                        "customer_id": customer.get("id"),
                        "customer_name": customer.get("name"),
                        "intent_level": intent_level,
                        "days_since_contact": days_since,
                        "priority": self._get_priority(intent_level, days_since)
                    })
            else:
                # 从未联系过的新客户
                plans.append({
                    "customer_id": customer.get("id"),
                    "customer_name": customer.get("name"),
                    "intent_level": intent_level,
                    "days_since_contact": 999,
                    "priority": 1  # 高优先级
                })
        
        # 按优先级排序
        plans.sort(key=lambda x: x["priority"])
        
        self.log(f"生成批量跟进计划: {len(plans)} 个客户待跟进")
        
        return plans
    
    def _get_priority(self, intent_level: str, days_since: int) -> int:
        """
        计算跟进优先级（1最高）
        """
        base_priority = {"S": 1, "A": 2, "B": 3, "C": 4}.get(intent_level, 5)
        
        # 超期越多优先级越高
        interval = self.FOLLOW_INTERVALS.get(intent_level, 7)
        overdue_factor = days_since / interval
        
        return int(base_priority / overdue_factor) if overdue_factor > 1 else base_priority
    
    async def handle_no_response(
        self, 
        customer_id: str, 
        no_response_count: int
    ) -> Dict[str, Any]:
        """
        处理客户无响应情况
        """
        if no_response_count >= 3:
            # 连续3次无响应，降低跟进频率
            return {
                "action": "reduce_frequency",
                "message": "客户连续3次无响应，建议降低跟进频率",
                "new_interval_days": 30
            }
        elif no_response_count >= 5:
            # 连续5次无响应，转入冷藏池
            return {
                "action": "archive",
                "message": "客户多次无响应，建议转入冷藏池",
                "reactivate_after_days": 90
            }
        else:
            return {
                "action": "continue",
                "message": f"继续跟进，当前无响应次数: {no_response_count}"
            }


# 创建单例并注册
follow_agent = FollowAgent()
AgentRegistry.register(follow_agent)
