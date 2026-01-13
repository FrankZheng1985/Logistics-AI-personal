"""
AI员工基类
所有AI员工都继承自这个基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from loguru import logger

from app.core.llm import chat_completion
from app.models.conversation import AgentType


class BaseAgent(ABC):
    """AI员工基类"""
    
    # 子类必须定义这些属性
    name: str = "未命名"
    agent_type: AgentType = None
    description: str = ""
    
    def __init__(self):
        self.system_prompt = self._build_system_prompt()
        logger.info(f"🤖 {self.name} 初始化完成")
    
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
