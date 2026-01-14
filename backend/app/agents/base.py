"""
AI员工基类
所有AI员工都继承自这个基类
集成物流专业老人级别知识库
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from loguru import logger

from app.core.llm import chat_completion
from app.models.conversation import AgentType
from app.core.prompts.logistics_expert import LOGISTICS_EXPERT_BASE_PROMPT


class BaseAgent(ABC):
    """AI员工基类
    
    所有AI员工都具备专业物流老人级别的知识水平
    """
    
    # 子类必须定义这些属性
    name: str = "未命名"
    agent_type: AgentType = None
    description: str = ""
    
    # 是否启用专业物流知识
    enable_logistics_expertise: bool = True
    
    def __init__(self):
        self.system_prompt = self._build_full_system_prompt()
        logger.info(f"🤖 {self.name} 初始化完成 (物流专家模式: {'开启' if self.enable_logistics_expertise else '关闭'})")
    
    def _build_full_system_prompt(self) -> str:
        """构建完整的系统提示词，包含专业知识"""
        base_prompt = self._build_system_prompt()
        
        if self.enable_logistics_expertise:
            # 集成物流专业知识
            expertise_intro = """

## 专业背景
你具备15年国际物流从业经验的专业水准：
- 熟悉海运、空运、铁路、快递等全物流链条
- 精通各国清关政策和流程
- 了解危险品、敏感品处理规范
- 掌握报价策略和成本控制技巧
- 深谙客户痛点和解决方案

在回答问题和处理任务时，请运用你的专业知识，给出专业、可靠的建议。
"""
            return base_prompt + expertise_intro
        
        return base_prompt
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """构建系统提示词，子类必须实现"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务，子类必须实现"""
        pass
    
    async def think(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7
    ) -> str:
        """
        调用LLM进行思考
        
        Args:
            messages: 对话消息列表
            temperature: 创造性参数
        
        Returns:
            AI回复内容
        """
        try:
            response = await chat_completion(
                messages=messages,
                system_prompt=self.system_prompt,
                temperature=temperature
            )
            return response
        except Exception as e:
            logger.error(f"{self.name} 思考出错: {e}")
            raise
    
    async def chat(self, user_message: str, context: Optional[str] = None) -> str:
        """
        简单的单轮对话
        
        Args:
            user_message: 用户消息
            context: 额外上下文
        
        Returns:
            AI回复
        """
        messages = []
        
        if context:
            messages.append({"role": "user", "content": f"背景信息：{context}"})
            messages.append({"role": "assistant", "content": "好的，我已了解背景信息。"})
        
        messages.append({"role": "user", "content": user_message})
        
        return await self.think(messages)
    
    def log(self, message: str, level: str = "info"):
        """记录日志"""
        log_message = f"[{self.name}] {message}"
        getattr(logger, level)(log_message)


class AgentRegistry:
    """AI员工注册表"""
    
    _agents: Dict[AgentType, BaseAgent] = {}
    
    @classmethod
    def register(cls, agent: BaseAgent):
        """注册AI员工"""
        cls._agents[agent.agent_type] = agent
        logger.info(f"✓ {agent.name} 已注册")
    
    @classmethod
    def get(cls, agent_type: AgentType) -> Optional[BaseAgent]:
        """获取AI员工"""
        return cls._agents.get(agent_type)
    
    @classmethod
    def get_all(cls) -> Dict[AgentType, BaseAgent]:
        """获取所有AI员工"""
        return cls._agents.copy()
