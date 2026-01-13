"""
小销 - 销售客服
负责首次接待、解答咨询、收集需求
"""
from typing import Dict, Any, Optional, List
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.prompts.sales import SALES_SYSTEM_PROMPT, CHAT_RESPONSE_PROMPT


class SalesAgent(BaseAgent):
    """小销 - 销售客服"""
    
    name = "小销"
    agent_type = AgentType.SALES
    description = "销售客服 - 负责首次接待、解答咨询、收集需求"
    
    def _build_system_prompt(self) -> str:
        return SALES_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理客户对话
        
        Args:
            input_data: {
                "customer_id": "客户ID",
                "message": "客户消息",
                "customer_info": "客户信息（可选）",
                "chat_history": "对话历史（可选）"
            }
        
        Returns:
            {
                "reply": "回复内容",
                "intent_signals": ["识别到的意向信号"],
                "collected_info": {"收集到的信息"}
            }
        """
        customer_id = input_data.get("customer_id", "")
        message = input_data.get("message", "")
        customer_info = input_data.get("customer_info", "新客户，暂无信息")
        chat_history = input_data.get("chat_history", "无历史对话")
        
        # 构建对话提示
        chat_prompt = CHAT_RESPONSE_PROMPT.format(
            customer_info=customer_info,
            chat_history=chat_history,
            message=message
        )
        
        # 生成回复
        reply = await self.think([{"role": "user", "content": chat_prompt}])
        
        # 分析意向信号和收集的信息
        intent_signals = self._analyze_intent_signals(message)
        collected_info = self._extract_info(message)
        
        self.log(f"回复客户 {customer_id[:8]}...: {reply[:50]}...")
        
        return {
            "reply": reply,
            "intent_signals": intent_signals,
            "collected_info": collected_info
        }
    
    def _analyze_intent_signals(self, message: str) -> List[str]:
        """分析消息中的意向信号"""
        signals = []
        message_lower = message.lower()
        
        # 高意向信号
        if any(kw in message_lower for kw in ["报价", "价格", "多少钱", "费用", "运费"]):
            signals.append("ask_price")
        
        if any(kw in message_lower for kw in ["时效", "多久", "几天", "多长时间"]):
            signals.append("ask_transit_time")
        
        if any(kw in message_lower for kw in ["合作", "长期", "签约", "代理"]):
            signals.append("express_interest")
        
        # 信息提供信号
        if any(kw in message_lower for kw in ["kg", "公斤", "吨", "立方", "cbm"]):
            signals.append("provide_cargo_info")
        
        if any(kw in message_lower for kw in ["电话", "微信", "联系"]):
            signals.append("leave_contact")
        
        # 低意向信号
        if any(kw in message_lower for kw in ["随便问问", "了解一下", "暂时不"]):
            signals.append("just_asking")
        
        return signals
    
    def _extract_info(self, message: str) -> Dict[str, Any]:
        """从消息中提取有用信息"""
        info = {}
        
        # 提取货物信息
        # 这里可以用更复杂的NLP，暂时用简单规则
        if "kg" in message.lower() or "公斤" in message:
            info["has_weight_info"] = True
        
        if "cbm" in message.lower() or "立方" in message:
            info["has_volume_info"] = True
        
        # 提取目的地
        destinations = ["美国", "英国", "德国", "法国", "日本", "韩国", "澳洲", "东南亚"]
        for dest in destinations:
            if dest in message:
                info["destination"] = dest
                break
        
        return info
    
    async def greet_new_customer(self, customer_name: Optional[str] = None) -> str:
        """生成新客户问候语"""
        greeting_prompt = f"""
        请为一位新客户生成开场问候语。
        {"客户名称：" + customer_name if customer_name else "客户名称未知"}
        
        要求：
        1. 热情友好但不过分
        2. 简短有力
        3. 引导客户说出需求
        """
        
        return await self.think([{"role": "user", "content": greeting_prompt}])


# 创建单例并注册
sales_agent = SalesAgent()
AgentRegistry.register(sales_agent)
