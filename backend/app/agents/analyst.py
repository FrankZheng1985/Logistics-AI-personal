"""
小析 - 客户分析师
负责意向评分、客户画像、数据洞察
"""
from typing import Dict, Any, List
import json
from loguru import logger

from app.agents.base import BaseAgent, AgentRegistry
from app.models.conversation import AgentType
from app.core.config import settings
from app.core.prompts.analyst import ANALYST_SYSTEM_PROMPT, ANALYZE_CONVERSATION_PROMPT


class AnalystAgent(BaseAgent):
    """小析 - 客户分析师"""
    
    name = "小析"
    agent_type = AgentType.ANALYST
    description = "客户分析师 - 负责意向评分、客户画像、数据报表"
    
    # 意向评分规则
    SCORE_RULES = {
        "ask_price": settings.INTENT_SCORE_ASK_PRICE,
        "provide_cargo_info": settings.INTENT_SCORE_PROVIDE_CARGO,
        "ask_transit_time": settings.INTENT_SCORE_ASK_TRANSIT,
        "multiple_interactions": settings.INTENT_SCORE_MULTIPLE_INTERACTIONS,
        "leave_contact": settings.INTENT_SCORE_LEAVE_CONTACT,
        "express_interest": settings.INTENT_SCORE_EXPRESS_INTEREST,
        "just_asking": settings.INTENT_SCORE_JUST_ASKING,
    }
    
    def _build_system_prompt(self) -> str:
        return ANALYST_SYSTEM_PROMPT
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析客户意向
        
        Args:
            input_data: {
                "customer_info": "客户基础信息",
                "conversations": "对话列表",
                "intent_signals": ["已识别的意向信号"]
            }
        
        Returns:
            {
                "intent_score": 分数,
                "intent_level": "等级",
                "score_delta": 变化值,
                "analysis": "详细分析",
                "should_notify": bool
            }
        """
        customer_info = input_data.get("customer_info", {})
        conversations = input_data.get("conversations", [])
        intent_signals = input_data.get("intent_signals", [])
        current_score = input_data.get("current_score", 0)
        
        # 方法1：基于规则计算分数增量
        rule_based_delta = self._calculate_score_delta(intent_signals)
        
        # 方法2：使用AI进行深度分析
        if conversations:
            ai_analysis = await self._ai_analyze(customer_info, conversations)
        else:
            ai_analysis = None
        
        # 综合评估
        final_delta = rule_based_delta
        new_score = max(0, current_score + final_delta)
        intent_level = self._get_intent_level(new_score)
        
        # 是否需要通知老板
        should_notify = (
            new_score >= settings.HIGH_INTENT_THRESHOLD and 
            current_score < settings.HIGH_INTENT_THRESHOLD
        )
        
        result = {
            "intent_score": new_score,
            "intent_level": intent_level,
            "score_delta": final_delta,
            "signals_detected": intent_signals,
            "analysis": ai_analysis,
            "should_notify": should_notify
        }
        
        self.log(f"意向分析完成: {intent_level}级 ({new_score}分, Δ{final_delta})")
        
        if should_notify:
            self.log(f"⚡ 发现高意向客户！需要通知老板", "warning")
        
        return result
    
    def _calculate_score_delta(self, signals: List[str]) -> int:
        """根据意向信号计算分数增量"""
        delta = 0
        for signal in signals:
            if signal in self.SCORE_RULES:
                delta += self.SCORE_RULES[signal]
        return delta
    
    def _get_intent_level(self, score: int) -> str:
        """根据分数获取意向等级"""
        if score >= 80:
            return "S"
        elif score >= 60:
            return "A"
        elif score >= 30:
            return "B"
        else:
            return "C"
    
    async def _ai_analyze(
        self, 
        customer_info: Dict[str, Any], 
        conversations: List[Dict]
    ) -> Dict[str, Any]:
        """使用AI进行深度分析"""
        # 格式化对话内容
        conv_text = "\n".join([
            f"[{c.get('type', 'unknown')}] {c.get('content', '')}"
            for c in conversations
        ])
        
        # 构建分析提示
        analysis_prompt = ANALYZE_CONVERSATION_PROMPT.format(
            customer_info=json.dumps(customer_info, ensure_ascii=False),
            conversations=conv_text
        )
        
        # 调用AI分析
        response = await self.think(
            [{"role": "user", "content": analysis_prompt}],
            temperature=0.3  # 分析任务用较低温度
        )
        
        # 解析结果
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            pass
        
        return {"raw_analysis": response}
    
    async def generate_customer_profile(
        self, 
        customer_info: Dict[str, Any],
        conversations: List[Dict]
    ) -> Dict[str, Any]:
        """生成客户画像"""
        profile_prompt = f"""
        请根据以下信息生成客户画像：
        
        基础信息：{json.dumps(customer_info, ensure_ascii=False)}
        
        对话记录：
        {json.dumps(conversations, ensure_ascii=False)}
        
        请分析并输出：
        1. 客户类型（个人/企业/货代同行）
        2. 业务规模（小/中/大）
        3. 主要需求（货物类型、航线）
        4. 决策特征（快速/犹豫/价格敏感）
        5. 跟进策略建议
        """
        
        response = await self.think([{"role": "user", "content": profile_prompt}])
        return {"profile": response}


# 创建单例并注册
analyst_agent = AnalystAgent()
AgentRegistry.register(analyst_agent)
