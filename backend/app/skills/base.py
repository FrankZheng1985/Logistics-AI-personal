"""
BaseSkill - 所有Skill的抽象基类

设计原则:
1. 每个Skill只做一件事（单一职责）
2. Skill之间不直接调用，通过Agent编排
3. 标准化的输入/输出格式
4. 内置错误处理和日志
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from loguru import logger

from app.models.database import AsyncSessionLocal
from sqlalchemy import text


class SkillRegistry:
    """技能注册表 - 管理所有已注册的Skill实例"""
    
    _skills: Dict[str, "BaseSkill"] = {}
    
    @classmethod
    def register(cls, skill: "BaseSkill"):
        """注册一个Skill实例"""
        cls._skills[skill.name] = skill
        logger.debug(f"[SkillRegistry] 注册技能: {skill.name}")
    
    @classmethod
    def get(cls, name: str) -> Optional["BaseSkill"]:
        """获取Skill实例"""
        return cls._skills.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, "BaseSkill"]:
        """获取所有Skill"""
        return cls._skills.copy()
    
    @classmethod
    def get_tool_mapping(cls) -> Dict[str, "BaseSkill"]:
        """获取 tool_name -> skill 的映射表（用于 MariaToolExecutor 路由）"""
        mapping = {}
        for skill in cls._skills.values():
            for tool_name in skill.tool_names:
                mapping[tool_name] = skill
        return mapping


class BaseSkill(ABC):
    """
    技能基类
    
    每个Skill需要实现:
    - name: 技能名称（唯一标识）
    - description: 技能描述
    - tool_names: 该技能处理的工具名称列表
    - handle(): 处理工具调用的核心方法
    """
    
    # 子类必须覆盖
    name: str = ""
    description: str = ""
    tool_names: List[str] = []
    
    def __init__(self, agent=None):
        """
        初始化Skill
        
        Args:
            agent: ClauwdbotAgent实例引用（用于访问chat/think等LLM方法和日志）
        """
        self.agent = agent
    
    @abstractmethod
    async def handle(self, tool_name: str, args: Dict[str, Any], 
                     message: str = "", user_id: str = "") -> Dict[str, Any]:
        """
        处理工具调用
        
        Args:
            tool_name: 被调用的工具名称
            args: 工具参数（来自LLM的function calling）
            message: 用户原始消息
            user_id: 用户ID
            
        Returns:
            标准化结果字典，至少包含:
            - "status": "success" | "error"
            - "message": 人类可读的结果描述
            可选:
            - "response": 直接回复给用户的文本
            - "filepath": 生成的文件路径
            - "data": 结构化数据
        """
        pass
    
    # ==================== 便捷方法 ====================
    
    async def log_step(self, step_type: str, title: str, detail: str = ""):
        """记录步骤日志（如果有agent引用）"""
        if self.agent:
            await self.agent.log_live_step(step_type, title, detail)
    
    async def think(self, messages: List[Dict], temperature: float = 0.3) -> str:
        """调用LLM思考（通过agent）"""
        if self.agent:
            return await self.agent.think(messages, temperature=temperature)
        raise RuntimeError("Skill未绑定Agent，无法调用LLM")
    
    async def chat(self, message: str, system_prompt: str = "") -> str:
        """调用LLM聊天（通过agent）"""
        if self.agent:
            return await self.agent.chat(message, system_prompt)
        raise RuntimeError("Skill未绑定Agent，无法调用LLM")
    
    async def db_execute(self, query: str, params: Dict = None) -> Any:
        """执行数据库查询（便捷方法）"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(text(query), params or {})
            return result
    
    async def db_execute_commit(self, query: str, params: Dict = None) -> Any:
        """执行数据库写入并提交"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(text(query), params or {})
            await db.commit()
            return result
    
    def _ok(self, response: str = "", **kwargs) -> Dict[str, Any]:
        """构造成功结果"""
        result = {"success": True, "status": "success", "response": response}
        result.update(kwargs)
        return result
    
    def _err(self, message: str, **kwargs) -> Dict[str, Any]:
        """构造错误结果"""
        result = {"success": False, "status": "error", "message": message}
        result.update(kwargs)
        return result
